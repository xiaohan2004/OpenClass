"""Transcribe local videos with DashScope ASR and write segmented text files.

This script calls Alibaba Cloud DashScope directly. It does not call the local
OpenClass backend. The API key is loaded from .env in the current working
directory with the QWEN_API_KEY variable.

Examples:
    python scripts/transcribe_videos_dashscope.py E:\videos\lesson1.mp4
    python scripts/transcribe_videos_dashscope.py E:\videos
    python scripts/transcribe_videos_dashscope.py --videos E:\videos\lesson1.mp4
    python scripts/transcribe_videos_dashscope.py --input-dir E:\videos --output-dir data\transcripts
    python scripts/transcribe_videos_dashscope.py --csv data\transcribe_batch.csv

CSV columns:
    video_path      required
    output_stem     optional, defaults to the video file name
"""

from __future__ import annotations

import argparse
import base64
import csv
import json
import math
import os
import random
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import dashscope

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - optional convenience dependency
    load_dotenv = None


DEFAULT_MODEL = "qwen3-asr-flash"
DEFAULT_BASE_URL = "https://dashscope.aliyuncs.com/api/v1"
DEFAULT_LANGUAGE = "zh"
DEFAULT_CHUNK_SECONDS = 5
DEFAULT_CONCURRENCY = 100
DEFAULT_RPM_LIMIT = 100
DEFAULT_MAX_RETRIES = 3
DEFAULT_RETRY_BACKOFF_SECONDS = 2.0
DEFAULT_PREFETCH_CHUNKS = 30
MEDIA_EXTENSIONS = {
    ".mp4",
    ".mkv",
    ".mov",
    ".avi",
    ".wmv",
    ".flv",
    ".webm",
    ".m4v",
    ".mp3",
    ".wav",
    ".m4a",
    ".aac",
    ".flac",
    ".ogg",
    ".opus",
}


@dataclass
class VideoJob:
    row_label: str
    video_path: Path
    output_stem: str


@dataclass
class Segment:
    seq: int
    start_time: float
    end_time: float
    text: str


@dataclass
class JobResult:
    job: VideoJob
    ok: bool
    segments: int = 0
    jsonl_path: Path | None = None
    txt_path: Path | None = None
    error: str | None = None


@dataclass
class ChunkTask:
    index: int
    chunk_path: Path
    start_time: float
    end_time: float
    total_chunks: int


class EmptyTranscriptError(RuntimeError):
    pass


def is_empty_audio_error(message: str) -> bool:
    lowered = message.lower()
    return "audio is empty" in lowered or "empty audio" in lowered


class SmoothRateLimiter:
    def __init__(self, rpm: int) -> None:
        if rpm <= 0:
            raise ValueError("--rpm-limit must be greater than 0")
        self._interval_seconds = 60.0 / rpm
        self._next_start_time = time.monotonic()
        self._lock = threading.Lock()

    def wait(self) -> None:
        with self._lock:
            now = time.monotonic()
            wait_seconds = max(0.0, self._next_start_time - now)
            self._next_start_time = max(now, self._next_start_time) + self._interval_seconds
        if wait_seconds > 0:
            time.sleep(wait_seconds)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Transcribe videos with DashScope ASR and output segmented text."
    )
    parser.add_argument(
        "paths",
        nargs="*",
        help="Input file or directory paths. A directory is scanned for media files.",
    )
    parser.add_argument("--videos", nargs="+", help="One or more local video files.")
    parser.add_argument("--input-dir", help="Directory containing video files.")
    parser.add_argument("--csv", help="CSV file containing video_path rows.")

    parser.add_argument("--output-dir", default="data/transcripts")
    parser.add_argument(
        "--api-key-env",
        default="QWEN_API_KEY",
        help="Environment variable name read from current directory .env.",
    )
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--language", default=DEFAULT_LANGUAGE)
    parser.add_argument("--enable-itn", action="store_true")
    parser.add_argument("--chunk-seconds", type=int, default=DEFAULT_CHUNK_SECONDS)
    parser.add_argument(
        "--concurrency",
        type=int,
        default=DEFAULT_CONCURRENCY,
        help="Number of audio chunks to transcribe concurrently.",
    )
    parser.add_argument(
        "--rpm-limit",
        type=int,
        default=DEFAULT_RPM_LIMIT,
        help="Maximum DashScope requests started per minute.",
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=DEFAULT_MAX_RETRIES,
        help="Maximum retry attempts for one failed audio chunk.",
    )
    parser.add_argument(
        "--retry-backoff",
        type=float,
        default=DEFAULT_RETRY_BACKOFF_SECONDS,
        help="Base seconds for exponential retry backoff.",
    )
    parser.add_argument(
        "--no-resume",
        action="store_true",
        help="Ignore existing temporary transcript checkpoint.",
    )
    parser.add_argument(
        "--prefetch-chunks",
        type=int,
        default=DEFAULT_PREFETCH_CHUNKS,
        help="Maximum pending chunk files kept ahead of completed ASR work.",
    )
    parser.add_argument(
        "--formats",
        nargs="+",
        choices=("jsonl", "txt"),
        default=["jsonl", "txt"],
        help="Output formats. jsonl is recommended for later processing.",
    )
    parser.add_argument(
        "--audio-format",
        choices=("webm", "wav"),
        default="webm",
        help="Temporary audio chunk format sent to DashScope.",
    )
    parser.add_argument("--keep-chunks", action="store_true")
    return parser.parse_args()


def load_env_files() -> None:
    if load_dotenv is None:
        return
    load_dotenv(Path.cwd() / ".env", override=False)


def require_command(command: str) -> None:
    if shutil.which(command) is None:
        raise RuntimeError(
            f"Required command not found: {command}. Install FFmpeg and add it to PATH."
        )


def text_or_none(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def load_jobs(args: argparse.Namespace) -> list[VideoJob]:
    jobs: list[VideoJob] = []

    for raw_path in args.paths:
        path = Path(raw_path).expanduser()
        if path.is_dir():
            jobs.extend(load_jobs_from_dir(path, row_prefix=f"path:{path.name}"))
        else:
            jobs.append(
                VideoJob(
                    row_label=f"path#{len(jobs) + 1}",
                    video_path=path,
                    output_stem=path.stem,
                )
            )

    if args.videos:
        for video in args.videos:
            video_path = Path(video).expanduser()
            jobs.append(
                VideoJob(
                    row_label=f"arg#{len(jobs) + 1}",
                    video_path=video_path,
                    output_stem=video_path.stem,
                )
            )

    if args.input_dir:
        input_dir = Path(args.input_dir).expanduser()
        jobs.extend(load_jobs_from_dir(input_dir, row_prefix="dir"))

    if args.csv:
        jobs.extend(load_jobs_from_csv(Path(args.csv).expanduser()))

    if not jobs:
        raise ValueError(
            "No input provided. Pass a file path, a directory path, --videos, --input-dir, or --csv."
        )

    return jobs


def load_jobs_from_dir(input_dir: Path, row_prefix: str) -> list[VideoJob]:
    if not input_dir.exists():
        raise FileNotFoundError(f"Input directory does not exist: {input_dir}")
    if not input_dir.is_dir():
        raise NotADirectoryError(f"Input path is not a directory: {input_dir}")

    media_files = sorted(
        path
        for path in input_dir.iterdir()
        if path.is_file() and path.suffix.lower() in MEDIA_EXTENSIONS
    )
    return [
        VideoJob(row_label=f"{row_prefix}#{index}", video_path=path, output_stem=path.stem)
        for index, path in enumerate(media_files, start=1)
    ]


def load_jobs_from_csv(csv_path: Path) -> list[VideoJob]:
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file does not exist: {csv_path}")

    jobs: list[VideoJob] = []
    with csv_path.open("r", encoding="utf-8-sig", newline="") as file_obj:
        reader = csv.DictReader(file_obj)
        if not reader.fieldnames or "video_path" not in reader.fieldnames:
            raise ValueError("CSV must contain a video_path column")
        for row_number, row in enumerate(reader, start=2):
            raw_video_path = text_or_none(row.get("video_path"))
            if raw_video_path is None:
                raise ValueError(f"Row {row_number}: video_path is required")
            video_path = Path(raw_video_path).expanduser()
            output_stem = text_or_none(row.get("output_stem")) or video_path.stem
            jobs.append(
                VideoJob(
                    row_label=f"row {row_number}",
                    video_path=video_path,
                    output_stem=output_stem,
                )
            )
    return jobs


def get_video_duration(video_path: Path) -> float:
    command = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(video_path),
    ]
    result = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "ffprobe failed")
    try:
        return float(result.stdout.strip())
    except ValueError as exc:
        raise RuntimeError(f"Cannot parse video duration: {result.stdout!r}") from exc


def extract_audio_chunk(
    *,
    video_path: Path,
    task: ChunkTask,
    audio_format: str,
) -> Path:
    if audio_format == "webm":
        audio_args = ["-c:a", "libopus", "-b:a", "32k", "-f", "webm"]
    else:
        audio_args = ["-c:a", "pcm_s16le", "-f", "wav"]

    duration = max(0.0, task.end_time - task.start_time)
    command = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-ss",
        f"{task.start_time:.3f}",
        "-t",
        f"{duration:.3f}",
        "-i",
        str(video_path),
        "-vn",
        "-ac",
        "1",
        "-ar",
        "16000",
        *audio_args,
        str(task.chunk_path),
    ]
    result = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"ffmpeg failed for chunk {task.index}/{task.total_chunks}: "
            f"{result.stderr.strip() or 'unknown error'}"
        )
    if not task.chunk_path.exists():
        task.chunk_path.touch()
    return task.chunk_path


def guess_audio_mime_type(audio_bytes: bytes) -> str:
    if audio_bytes.startswith(b"ID3") or audio_bytes[:2] == b"\xff\xfb":
        return "audio/mpeg"
    if audio_bytes.startswith(b"RIFF") and audio_bytes[8:12] == b"WAVE":
        return "audio/wav"
    if audio_bytes.startswith(b"OggS"):
        return "audio/ogg"
    if audio_bytes.startswith(b"fLaC"):
        return "audio/flac"
    if audio_bytes.startswith(b"\x1a\x45\xdf\xa3"):
        return "audio/webm"
    if len(audio_bytes) > 12 and audio_bytes[4:8] == b"ftyp":
        return "audio/mp4"
    return "audio/wav"


def build_data_uri(audio_bytes: bytes) -> str:
    mime_type = guess_audio_mime_type(audio_bytes)
    base64_str = base64.b64encode(audio_bytes).decode("utf-8")
    return f"data:{mime_type};base64,{base64_str}"


def get_response_field(value: Any, field: str, default: Any = None) -> Any:
    if isinstance(value, dict):
        return value.get(field, default)
    return getattr(value, field, default)


def summarize_response(response: Any) -> str:
    try:
        if isinstance(response, dict):
            payload = response
        elif hasattr(response, "to_dict"):
            payload = response.to_dict()
        elif hasattr(response, "__dict__"):
            payload = response.__dict__
        else:
            payload = str(response)
        text = json.dumps(payload, ensure_ascii=False, default=str)
    except Exception:
        text = str(response)
    return text[:1000]


def extract_text_from_response(response: Any) -> str:
    output = get_response_field(response, "output")
    if output is None:
        return ""

    choices = get_response_field(output, "choices")
    if not choices:
        return ""

    first_choice = choices[0]
    message = get_response_field(first_choice, "message")
    if message is None:
        return ""

    content = get_response_field(message, "content")
    if isinstance(content, str):
        return content.strip()

    if not isinstance(content, list):
        return ""

    parts: list[str] = []
    for item in content:
        text = get_response_field(item, "text")
        if isinstance(text, str) and text.strip():
            parts.append(text.strip())
            continue
        audio_item = get_response_field(item, "audio")
        nested_text = get_response_field(audio_item, "text")
        if isinstance(nested_text, str) and nested_text.strip():
            parts.append(nested_text.strip())

    return "\n".join(parts).strip()


def transcribe_audio_chunk(
    *,
    chunk_path: Path,
    api_key: str,
    model: str,
    base_url: str,
    language: str | None,
    enable_itn: bool,
) -> str:
    audio_bytes = chunk_path.read_bytes()
    if not audio_bytes:
        raise EmptyTranscriptError(f"Audio chunk is empty: {chunk_path}")

    dashscope.base_http_api_url = base_url
    asr_options: dict[str, Any] = {"enable_itn": enable_itn}
    if language:
        asr_options["language"] = language

    response = dashscope.MultiModalConversation.call(
        api_key=api_key,
        model=model,
        messages=[{"role": "user", "content": [{"audio": build_data_uri(audio_bytes)}]}],
        result_format="message",
        asr_options=asr_options,
    )

    status_code = getattr(response, "status_code", None)
    if status_code is not None and status_code != 200:
        message = getattr(response, "message", "unknown error")
        if is_empty_audio_error(str(message)):
            raise EmptyTranscriptError(f"DashScope ASR returned empty audio: {message}")
        raise RuntimeError(f"DashScope ASR failed: {message}")

    text = extract_text_from_response(response)
    if not text:
        raise EmptyTranscriptError(
            "DashScope ASR returned no transcript text. "
            f"Response summary: {summarize_response(response)}"
        )
    return text


def format_timestamp(seconds: float) -> str:
    total_seconds = int(seconds)
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    secs = total_seconds % 60
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def segment_to_record(job: VideoJob, segment: Segment) -> dict[str, Any]:
    return {
        "seq": segment.seq,
        "video_path": str(job.video_path),
        "start_time": segment.start_time,
        "end_time": segment.end_time,
        "text": segment.text,
    }


def segment_from_record(record: dict[str, Any]) -> Segment:
    return Segment(
        seq=int(record["seq"]),
        start_time=float(record["start_time"]),
        end_time=float(record["end_time"]),
        text=str(record.get("text") or ""),
    )


def load_checkpoint_segments(path: Path) -> list[Segment]:
    if not path.exists():
        return []

    segments_by_seq: dict[int, Segment] = {}
    with path.open("r", encoding="utf-8-sig") as file_obj:
        for line_number, line in enumerate(file_obj, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                segment = segment_from_record(json.loads(stripped))
            except Exception as exc:
                raise RuntimeError(
                    f"Cannot parse checkpoint {path} line {line_number}: {exc}"
                ) from exc
            segments_by_seq[segment.seq] = segment
    return sorted(segments_by_seq.values(), key=lambda segment: segment.seq)


def append_checkpoint_segment(path: Path, job: VideoJob, segment: Segment) -> None:
    with path.open("a", encoding="utf-8", newline="\n") as file_obj:
        file_obj.write(json.dumps(segment_to_record(job, segment), ensure_ascii=False))
        file_obj.write("\n")
        file_obj.flush()


def write_jsonl(path: Path, job: VideoJob, segments: list[Segment]) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as file_obj:
        for segment in segments:
            file_obj.write(json.dumps(segment_to_record(job, segment), ensure_ascii=False))
            file_obj.write("\n")


def write_txt(path: Path, segments: list[Segment]) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as file_obj:
        for segment in segments:
            file_obj.write(
                f"[{format_timestamp(segment.start_time)} - "
                f"{format_timestamp(segment.end_time)}]\n"
            )
            file_obj.write(segment.text)
            file_obj.write("\n\n")


def transcribe_chunk_task(
    *,
    task: ChunkTask,
    job_label: str,
    api_key: str,
    model: str,
    base_url: str,
    language: str | None,
    enable_itn: bool,
    rate_limiter: SmoothRateLimiter,
    max_retries: int,
    retry_backoff: float,
    delete_chunk: bool,
) -> Segment | None:
    started_at = time.perf_counter()
    last_error: Exception | None = None
    text: str | None = None
    try:
        for attempt in range(1, max_retries + 2):
            try:
                rate_limiter.wait()
                text = transcribe_audio_chunk(
                    chunk_path=task.chunk_path,
                    api_key=api_key,
                    model=model,
                    base_url=base_url,
                    language=language,
                    enable_itn=enable_itn,
                )
                break
            except EmptyTranscriptError:
                elapsed = time.perf_counter() - started_at
                print(
                    f"[{job_label}] chunk {task.index}/{task.total_chunks} "
                    f"{format_timestamp(task.start_time)}-{format_timestamp(task.end_time)} "
                    f"no transcript, recorded empty, elapsed={elapsed:.1f}s"
                )
                return Segment(
                    seq=task.index,
                    start_time=round(task.start_time, 3),
                    end_time=round(task.end_time, 3),
                    text="",
                )
            except Exception as exc:
                last_error = exc
                if attempt > max_retries:
                    break
                sleep_seconds = (
                    retry_backoff * (2 ** (attempt - 1)) + random.uniform(0.0, 0.5)
                )
                print(
                    f"[{job_label}] chunk {task.index}/{task.total_chunks} "
                    f"failed attempt {attempt}/{max_retries + 1}: {exc}; "
                    f"retrying in {sleep_seconds:.1f}s"
                )
                time.sleep(sleep_seconds)
        else:  # pragma: no cover - defensive guard
            last_error = RuntimeError("unknown retry failure")
    finally:
        if delete_chunk:
            try:
                task.chunk_path.unlink(missing_ok=True)
            except OSError:
                pass

    if text is None:
        raise RuntimeError(
            f"chunk {task.index}/{task.total_chunks} failed after "
            f"{max_retries + 1} attempts: {last_error}"
        ) from last_error

    elapsed = time.perf_counter() - started_at
    print(
        f"[{job_label}] chunk {task.index}/{task.total_chunks} "
        f"{format_timestamp(task.start_time)}-{format_timestamp(task.end_time)} "
        f"completed, elapsed={elapsed:.1f}s"
    )
    return Segment(
        seq=task.index,
        start_time=round(task.start_time, 3),
        end_time=round(task.end_time, 3),
        text=text,
    )


def transcribe_chunks_concurrently(
    *,
    chunk_tasks: list[ChunkTask],
    job: VideoJob,
    temp_dir: Path,
    api_key: str,
    model: str,
    base_url: str,
    language: str | None,
    enable_itn: bool,
    concurrency: int,
    rpm_limit: int,
    max_retries: int,
    retry_backoff: float,
    prefetch_chunks: int,
    audio_format: str,
    keep_chunks: bool,
    checkpoint_path: Path,
    completed_segments: list[Segment],
) -> list[Segment]:
    if not chunk_tasks:
        return sorted(completed_segments, key=lambda segment: segment.seq)

    job_label = job.row_label
    worker_count = min(concurrency, prefetch_chunks, len(chunk_tasks))
    rate_limiter = SmoothRateLimiter(rpm_limit)
    print(
        f"[{job_label}] chunks={len(chunk_tasks)}, "
        f"concurrency={worker_count}, rpm_limit={rpm_limit}, "
        f"prefetch_chunks={prefetch_chunks}, temp_dir={temp_dir}"
    )

    segments: list[Segment] = list(completed_segments)
    errors: list[str] = []
    pending: dict[Any, ChunkTask] = {}

    def collect_done(done_futures: set[Any]) -> None:
        for future in done_futures:
            pending.pop(future, None)
            try:
                segment = future.result()
            except Exception as exc:
                errors.append(str(exc))
                continue
            if segment is not None:
                segments.append(segment)
                append_checkpoint_segment(checkpoint_path, job, segment)

    with ThreadPoolExecutor(max_workers=worker_count) as executor:
        for task in chunk_tasks:
            while len(pending) >= prefetch_chunks:
                done, _ = wait(pending.keys(), return_when=FIRST_COMPLETED)
                collect_done(done)

            extract_audio_chunk(
                video_path=job.video_path,
                task=task,
                audio_format=audio_format,
            )
            future = executor.submit(
                transcribe_chunk_task,
                task=task,
                job_label=job_label,
                api_key=api_key,
                model=model,
                base_url=base_url,
                language=language,
                enable_itn=enable_itn,
                rate_limiter=rate_limiter,
                max_retries=max_retries,
                retry_backoff=retry_backoff,
                delete_chunk=not keep_chunks,
            )
            pending[future] = task

            done_now = {future for future in pending if future.done()}
            collect_done(done_now)

        while pending:
            done, _ = wait(pending.keys(), return_when=FIRST_COMPLETED)
            collect_done(done)

    if errors:
        preview = "; ".join(errors[:3])
        if len(errors) > 3:
            preview += f"; ... ({len(errors)} chunks failed)"
        raise RuntimeError(preview)

    return sorted(segments, key=lambda segment: segment.seq)


def transcribe_job(args: argparse.Namespace, job: VideoJob, api_key: str) -> JobResult:
    output_dir = Path(args.output_dir).expanduser()
    output_dir.mkdir(parents=True, exist_ok=True)
    result = JobResult(job=job, ok=False)
    temp_dir_obj: tempfile.TemporaryDirectory[str] | None = None

    try:
        print(f"[{job.row_label}] 准备转写: {job.video_path}")
        if args.concurrency <= 0:
            raise ValueError("--concurrency must be greater than 0")
        if args.rpm_limit <= 0:
            raise ValueError("--rpm-limit must be greater than 0")
        if args.max_retries < 0:
            raise ValueError("--max-retries must be greater than or equal to 0")
        if args.retry_backoff < 0:
            raise ValueError("--retry-backoff must be greater than or equal to 0")
        if args.prefetch_chunks <= 0:
            raise ValueError("--prefetch-chunks must be greater than 0")

        duration = get_video_duration(job.video_path)

        temp_dir_obj = tempfile.TemporaryDirectory(prefix="dashscope_asr_chunks_")
        temp_dir = Path(temp_dir_obj.name)
        if args.chunk_seconds <= 0:
            raise ValueError("--chunk-seconds must be greater than 0")
        total_chunks = max(1, math.ceil(duration / args.chunk_seconds))

        chunk_tasks = [
            ChunkTask(
                index=index,
                chunk_path=temp_dir / f"chunk_{index:05d}.{args.audio_format}",
                start_time=float((index - 1) * args.chunk_seconds),
                end_time=min(float(index * args.chunk_seconds), duration),
                total_chunks=total_chunks,
            )
            for index in range(1, total_chunks + 1)
        ]
        checkpoint_path = output_dir / f"{job.output_stem}.transcript.tmp.jsonl"
        if args.no_resume and checkpoint_path.exists():
            checkpoint_path.unlink()

        completed_segments = load_checkpoint_segments(checkpoint_path)
        valid_seq_set = {task.index for task in chunk_tasks}
        completed_segments = [
            segment for segment in completed_segments if segment.seq in valid_seq_set
        ]
        completed_seq_set = {segment.seq for segment in completed_segments}
        remaining_tasks = [
            task for task in chunk_tasks if task.index not in completed_seq_set
        ]
        if completed_segments:
            print(
                f"[{job.row_label}] resumed {len(completed_segments)} "
                f"chunks from {checkpoint_path}"
            )

        segments = transcribe_chunks_concurrently(
            chunk_tasks=remaining_tasks,
            job=job,
            temp_dir=temp_dir,
            api_key=api_key,
            model=args.model,
            base_url=args.base_url,
            language=args.language,
            enable_itn=args.enable_itn,
            concurrency=args.concurrency,
            rpm_limit=args.rpm_limit,
            max_retries=args.max_retries,
            retry_backoff=args.retry_backoff,
            prefetch_chunks=args.prefetch_chunks,
            audio_format=args.audio_format,
            keep_chunks=args.keep_chunks,
            checkpoint_path=checkpoint_path,
            completed_segments=completed_segments,
        )
        if not any(segment.text for segment in segments):
            raise RuntimeError("DashScope ASR returned no transcript text for all chunks")

        if "jsonl" in args.formats:
            jsonl_path = output_dir / f"{job.output_stem}.transcript.jsonl"
            write_jsonl(jsonl_path, job, segments)
            result.jsonl_path = jsonl_path
        if "txt" in args.formats:
            txt_path = output_dir / f"{job.output_stem}.transcript.txt"
            write_txt(txt_path, segments)
            result.txt_path = txt_path
        if checkpoint_path.exists():
            checkpoint_path.unlink()

        result.ok = True
        result.segments = len(segments)
        print(f"[{job.row_label}] 完成: segments={len(segments)}")
    except Exception as exc:
        result.error = str(exc)
        print(f"[{job.row_label}] 失败: {exc}", file=sys.stderr)
    finally:
        if temp_dir_obj is not None and not args.keep_chunks:
            temp_dir_obj.cleanup()
        elif temp_dir_obj is not None:
            print(f"[{job.row_label}] 保留临时分片: {temp_dir_obj.name}")

    return result


def resolve_api_key(args: argparse.Namespace) -> str:
    api_key = os.environ.get(args.api_key_env)
    if not api_key:
        raise RuntimeError(
            f"DashScope API key is required. Put {args.api_key_env}=... in "
            f"{Path.cwd() / '.env'}."
        )
    return api_key


def main() -> int:
    args = parse_args()
    try:
        load_env_files()
        require_command("ffmpeg")
        require_command("ffprobe")
        api_key = resolve_api_key(args)
        jobs = load_jobs(args)
        if not jobs:
            print("没有找到可转写的视频")
            return 0

        results = [transcribe_job(args, job, api_key) for job in jobs]
        print("\n========== 转写结果 ==========")
        for item in results:
            status = "OK" if item.ok else "FAIL"
            print(
                f"[{status}] {item.job.row_label}, video={item.job.video_path}, "
                f"segments={item.segments}, jsonl={item.jsonl_path or ''}, "
                f"txt={item.txt_path or ''}, error={item.error or ''}"
            )

        failed_count = sum(1 for item in results if not item.ok)
        print(f"总数={len(results)}, 成功={len(results) - failed_count}, 失败={failed_count}")
        return 1 if failed_count else 0
    except KeyboardInterrupt:
        print("用户中断", file=sys.stderr)
        return 130
    except Exception as exc:
        print(f"运行失败: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
