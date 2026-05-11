"""Batch-run classroom simulations through the existing REST and WebSocket APIs.

CSV columns:
    video_path          required, local video file path
    session_title       optional, defaults to video file name
    course_id           optional, reuse an existing course when present
    course_code         optional, used to find or create a course
    course_name         optional
    teacher             optional
    description         optional
    start_time          optional Unix timestamp, defaults to current time
    generate_report     optional true/false, defaults to false

Example:
    python scripts/batch_classroom_runner.py --csv data/classroom_batch.csv
"""

from __future__ import annotations

import argparse
import asyncio
import base64
import csv
import json
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse, urlunparse
from urllib.request import Request, urlopen

import websockets


DEFAULT_BASE_URL = "http://127.0.0.1:8000"
DEFAULT_CHUNK_SECONDS = 5
DEFAULT_DRAIN_SECONDS = 30
DEFAULT_TRANSCRIPT_TIMEOUT_SECONDS = 180


class ApiError(RuntimeError):
    """Raised when the backend API returns an error response."""


@dataclass
class ClassroomJob:
    row_number: int
    video_path: Path
    session_title: str
    course_id: int | None
    course_code: str | None
    course_name: str | None
    teacher: str | None
    description: str | None
    start_time: int
    generate_report: bool


@dataclass
class JobResult:
    row_number: int
    video_path: Path
    ok: bool
    course_id: int | None = None
    session_id: int | None = None
    chunks_sent: int = 0
    transcripts_received: int = 0
    report_requested: bool = False
    error: str | None = None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Batch-run classroom simulations against OpenClass backend."
    )
    parser.add_argument("--csv", required=True, help="CSV file containing video jobs.")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--chunk-seconds", type=int, default=DEFAULT_CHUNK_SECONDS)
    parser.add_argument("--concurrency", type=int, default=1)
    parser.add_argument("--drain-seconds", type=int, default=DEFAULT_DRAIN_SECONDS)
    parser.add_argument(
        "--transcript-timeout",
        type=int,
        default=DEFAULT_TRANSCRIPT_TIMEOUT_SECONDS,
        help="Seconds to wait for transcript after each audio chunk.",
    )
    parser.add_argument(
        "--audio-format",
        choices=("webm", "wav"),
        default="webm",
        help="Temporary audio chunk format sent to the ASR backend.",
    )
    parser.add_argument(
        "--keep-chunks",
        action="store_true",
        help="Keep temporary audio chunks for debugging.",
    )
    return parser.parse_args()


def normalize_base_url(base_url: str) -> str:
    return base_url.rstrip("/")


def build_ws_url(base_url: str, session_id: int) -> str:
    parsed = urlparse(base_url)
    if parsed.scheme == "https":
        scheme = "wss"
    elif parsed.scheme == "http":
        scheme = "ws"
    else:
        raise ValueError(f"Unsupported base URL scheme: {parsed.scheme}")
    return urlunparse((scheme, parsed.netloc, f"/ws/session/{session_id}", "", "", ""))


def bool_from_cell(value: str | None) -> bool:
    if value is None:
        return False
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def text_or_none(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def int_or_none(value: str | None) -> int | None:
    stripped = text_or_none(value)
    if stripped is None:
        return None
    return int(stripped)


def load_jobs(csv_path: Path) -> list[ClassroomJob]:
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file does not exist: {csv_path}")

    jobs: list[ClassroomJob] = []
    with csv_path.open("r", encoding="utf-8-sig", newline="") as file_obj:
        reader = csv.DictReader(file_obj)
        if not reader.fieldnames or "video_path" not in reader.fieldnames:
            raise ValueError("CSV must contain a video_path column")

        for row_number, row in enumerate(reader, start=2):
            raw_video_path = text_or_none(row.get("video_path"))
            if raw_video_path is None:
                raise ValueError(f"Row {row_number}: video_path is required")

            video_path = Path(raw_video_path).expanduser()
            session_title = (
                text_or_none(row.get("session_title")) or video_path.stem or "批量课堂"
            )
            start_time = int_or_none(row.get("start_time")) or int(time.time())

            jobs.append(
                ClassroomJob(
                    row_number=row_number,
                    video_path=video_path,
                    session_title=session_title,
                    course_id=int_or_none(row.get("course_id")),
                    course_code=text_or_none(row.get("course_code")),
                    course_name=text_or_none(row.get("course_name")),
                    teacher=text_or_none(row.get("teacher")),
                    description=text_or_none(row.get("description")),
                    start_time=start_time,
                    generate_report=bool_from_cell(row.get("generate_report")),
                )
            )

    return jobs


def require_command(command: str) -> None:
    if shutil.which(command) is None:
        raise RuntimeError(
            f"Required command not found: {command}. Install FFmpeg and add it to PATH."
        )


def api_request(
    base_url: str,
    method: str,
    path: str,
    payload: dict[str, Any] | None = None,
    timeout: int = 30,
) -> Any:
    body = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = Request(
        f"{base_url}{path}",
        data=body,
        headers=headers,
        method=method.upper(),
    )

    try:
        with urlopen(request, timeout=timeout) as response:
            raw = response.read()
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise ApiError(f"{method} {path} failed: HTTP {exc.code} {detail}") from exc
    except URLError as exc:
        raise ApiError(f"{method} {path} failed: {exc}") from exc

    if not raw:
        return None

    data = json.loads(raw.decode("utf-8"))
    if isinstance(data, dict) and "code" in data and data.get("code") != 0:
        raise ApiError(f"{method} {path} failed: {data.get('msg')}")
    return data


def api_data(response: Any) -> Any:
    if isinstance(response, dict) and "data" in response:
        return response["data"]
    return response


def health_check(base_url: str) -> None:
    api_request(base_url, "GET", "/health")


def resolve_course_id(base_url: str, job: ClassroomJob) -> int:
    if job.course_id is not None:
        api_request(base_url, "GET", f"/api/courses/{job.course_id}")
        return job.course_id

    if job.course_code:
        courses = api_data(api_request(base_url, "GET", "/api/courses")) or []
        for course in courses:
            if course.get("code") == job.course_code:
                return int(course["id"])

    payload = {
        "code": job.course_code,
        "name": job.course_name or job.course_code or "批量导入课程",
        "description": job.description,
        "teacher": job.teacher,
    }
    created = api_data(api_request(base_url, "POST", "/api/courses", payload))
    return int(created["id"])


def create_session(base_url: str, course_id: int, title: str) -> int:
    payload = {"course_id": course_id, "title": title}
    created = api_data(api_request(base_url, "POST", "/api/sessions", payload))
    return int(created["id"])


def start_session(base_url: str, session_id: int, start_time: int) -> None:
    api_request(
        base_url,
        "POST",
        f"/api/sessions/{session_id}/start",
        {"start_time": start_time},
    )


def end_session(base_url: str, session_id: int, end_time: int) -> None:
    api_request(
        base_url,
        "POST",
        f"/api/sessions/{session_id}/end",
        {"end_time": end_time},
    )


def request_report(base_url: str, session_id: int) -> None:
    api_request(base_url, "POST", f"/api/sessions/{session_id}/reports", timeout=60)


def split_video_to_chunks(
    video_path: Path,
    output_dir: Path,
    chunk_seconds: int,
    audio_format: str,
) -> list[Path]:
    if not video_path.exists():
        raise FileNotFoundError(f"Video file does not exist: {video_path}")
    if chunk_seconds <= 0:
        raise ValueError("--chunk-seconds must be greater than 0")

    if audio_format == "webm":
        pattern = output_dir / "chunk_%05d.webm"
        audio_args = [
            "-c:a",
            "libopus",
            "-b:a",
            "32k",
            "-f",
            "segment",
            "-segment_format",
            "webm",
        ]
    else:
        pattern = output_dir / "chunk_%05d.wav"
        audio_args = [
            "-c:a",
            "pcm_s16le",
            "-f",
            "segment",
            "-segment_format",
            "wav",
        ]

    command = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-i",
        str(video_path),
        "-vn",
        "-ac",
        "1",
        "-ar",
        "16000",
        *audio_args,
        "-segment_time",
        str(chunk_seconds),
        "-reset_timestamps",
        "1",
        str(pattern),
    ]

    result = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "ffmpeg failed")

    chunks = sorted(output_dir.glob(f"chunk_*.{audio_format}"))
    if not chunks:
        raise RuntimeError(f"ffmpeg produced no audio chunks for {video_path}")
    return chunks


async def send_audio_chunks(
    ws_url: str,
    chunks: list[Path],
    start_time: int,
    chunk_seconds: int,
    transcript_timeout: int,
    drain_seconds: int,
) -> tuple[int, int]:
    chunks_sent = 0
    transcripts_received = 0

    async with websockets.connect(ws_url, max_size=None) as websocket:
        for index, chunk_path in enumerate(chunks):
            audio_base64 = base64.b64encode(chunk_path.read_bytes()).decode("ascii")
            chunk_start = start_time + index * chunk_seconds
            chunk_end = chunk_start + chunk_seconds
            payload = {
                "type": "audio_in",
                "data": {
                    "audio": audio_base64,
                    "start_time": chunk_start,
                    "end_time": chunk_end,
                },
            }
            await websocket.send(json.dumps(payload, ensure_ascii=False))
            chunks_sent += 1

            while True:
                raw_message = await asyncio.wait_for(
                    websocket.recv(), timeout=transcript_timeout
                )
                message = json.loads(raw_message)
                if message.get("type") == "error":
                    raise RuntimeError(f"WebSocket error: {message.get('data')}")
                if message.get("type") == "transcript":
                    transcripts_received += 1
                    break

        deadline = time.monotonic() + max(0, drain_seconds)
        while time.monotonic() < deadline:
            timeout = max(0.1, deadline - time.monotonic())
            try:
                await asyncio.wait_for(websocket.recv(), timeout=timeout)
            except asyncio.TimeoutError:
                break

    return chunks_sent, transcripts_received


async def run_job(
    base_url: str,
    job: ClassroomJob,
    chunk_seconds: int,
    audio_format: str,
    transcript_timeout: int,
    drain_seconds: int,
    keep_chunks: bool,
) -> JobResult:
    result = JobResult(row_number=job.row_number, video_path=job.video_path, ok=False)
    temp_dir_obj: tempfile.TemporaryDirectory[str] | None = None

    try:
        print(f"[row {job.row_number}] 准备处理: {job.video_path}")
        course_id = await asyncio.to_thread(resolve_course_id, base_url, job)
        session_id = await asyncio.to_thread(
            create_session, base_url, course_id, job.session_title
        )
        result.course_id = course_id
        result.session_id = session_id

        await asyncio.to_thread(start_session, base_url, session_id, job.start_time)

        temp_dir_obj = tempfile.TemporaryDirectory(prefix="openclass_chunks_")
        temp_dir = Path(temp_dir_obj.name)
        chunks = await asyncio.to_thread(
            split_video_to_chunks,
            job.video_path,
            temp_dir,
            chunk_seconds,
            audio_format,
        )

        ws_url = build_ws_url(base_url, session_id)
        print(
            f"[row {job.row_number}] session={session_id}, chunks={len(chunks)}, 开始发送"
        )
        chunks_sent, transcripts_received = await send_audio_chunks(
            ws_url,
            chunks,
            job.start_time,
            chunk_seconds,
            transcript_timeout,
            drain_seconds,
        )
        result.chunks_sent = chunks_sent
        result.transcripts_received = transcripts_received

        end_time = job.start_time + chunks_sent * chunk_seconds
        await asyncio.to_thread(end_session, base_url, session_id, end_time)

        if job.generate_report:
            await asyncio.to_thread(request_report, base_url, session_id)
            result.report_requested = True

        result.ok = True
        print(
            f"[row {job.row_number}] 完成: course={course_id}, session={session_id}, "
            f"sent={chunks_sent}, transcripts={transcripts_received}"
        )
    except Exception as exc:
        result.error = str(exc)
        print(f"[row {job.row_number}] 失败: {exc}", file=sys.stderr)
        if result.session_id is not None:
            try:
                await asyncio.to_thread(
                    end_session,
                    base_url,
                    result.session_id,
                    int(time.time()),
                )
            except Exception as end_exc:
                print(
                    f"[row {job.row_number}] 结束课堂失败: {end_exc}",
                    file=sys.stderr,
                )
    finally:
        if temp_dir_obj is not None and not keep_chunks:
            temp_dir_obj.cleanup()
        elif temp_dir_obj is not None:
            print(f"[row {job.row_number}] 保留临时分片: {temp_dir_obj.name}")

    return result


async def run_all(args: argparse.Namespace) -> int:
    base_url = normalize_base_url(args.base_url)
    csv_path = Path(args.csv).expanduser()

    require_command("ffmpeg")
    require_command("ffprobe")
    health_check(base_url)

    jobs = load_jobs(csv_path)
    if not jobs:
        print("CSV 中没有可运行的任务")
        return 0

    if args.concurrency <= 0:
        raise ValueError("--concurrency must be greater than 0")

    semaphore = asyncio.Semaphore(args.concurrency)

    async def guarded(job: ClassroomJob) -> JobResult:
        async with semaphore:
            return await run_job(
                base_url=base_url,
                job=job,
                chunk_seconds=args.chunk_seconds,
                audio_format=args.audio_format,
                transcript_timeout=args.transcript_timeout,
                drain_seconds=args.drain_seconds,
                keep_chunks=args.keep_chunks,
            )

    results = await asyncio.gather(*(guarded(job) for job in jobs))
    print("\n========== 批量运行结果 ==========")
    for item in results:
        status = "OK" if item.ok else "FAIL"
        print(
            f"[{status}] row={item.row_number}, video={item.video_path}, "
            f"course={item.course_id}, session={item.session_id}, "
            f"sent={item.chunks_sent}, transcripts={item.transcripts_received}, "
            f"report={item.report_requested}, error={item.error or ''}"
        )

    failed_count = sum(1 for item in results if not item.ok)
    print(f"总数={len(results)}, 成功={len(results) - failed_count}, 失败={failed_count}")
    return 1 if failed_count else 0


def main() -> int:
    args = parse_args()
    try:
        return asyncio.run(run_all(args))
    except KeyboardInterrupt:
        print("用户中断", file=sys.stderr)
        return 130
    except Exception as exc:
        print(f"运行失败: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
