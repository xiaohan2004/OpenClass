"""Backfill missing scores for generated questions.

Usage:
    python scripts/backfill_question_scores.py --dry-run
    python scripts/backfill_question_scores.py --limit 20
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import logging
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Any, Callable


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = PROJECT_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


logger = logging.getLogger(__name__)

QUESTION_QUALITY_DIMENSION_WEIGHTS = {
    "relevance": 0.35,
    "value": 0.25,
    "clarity": 0.15,
    "authenticity": 0.15,
    "brevity": 0.10,
}
DEFAULT_WORKERS = 1
MAX_WORKERS = 10


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Use the existing LLM question-quality evaluator to fill missing "
            "questions.score values from question_transcript_map context."
        )
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum number of questions to process.",
    )
    parser.add_argument(
        "--question-id",
        type=int,
        action="append",
        default=None,
        help="Only process the specified question id. Can be used multiple times.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-score selected questions even when score is already present.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Evaluate and print results without writing scores to the database.",
    )
    parser.add_argument(
        "--skip-missing-context",
        action="store_true",
        help="Skip questions that have no linked transcript text instead of failing.",
    )
    parser.add_argument(
        "--default-on-failure",
        type=float,
        default=None,
        help="Write this score when LLM evaluation fails. By default failures are not written.",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=None,
        help=(
            "Number of worker threads for concurrent LLM scoring. "
            "Defaults to question_concurrent_workers and is capped at 10."
        ),
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=("DEBUG", "INFO", "WARNING", "ERROR"),
        help="Logging verbosity.",
    )
    return parser.parse_args()


def get_default_workers() -> int:
    try:
        from app.config import get_settings

        return int(get_settings().question_concurrent_workers)
    except Exception as exc:
        logger.warning("无法读取 question_concurrent_workers，使用默认 workers=%d: %s", DEFAULT_WORKERS, exc)
        return DEFAULT_WORKERS


def normalize_workers(value: int | None) -> int:
    requested = get_default_workers() if value is None else int(value)
    workers = max(1, requested)
    if workers > MAX_WORKERS:
        logger.warning(
            "workers=%d 超过安全上限，已自动限制为 %d",
            workers,
            MAX_WORKERS,
        )
        return MAX_WORKERS
    return workers


def list_target_questions(
    db,
    *,
    question_ids: list[int] | None,
    force: bool,
    limit: int | None,
) -> list:
    from sqlmodel import select

    from app.db.models import Question

    statement = select(Question).order_by(Question.__table__.c.id.asc())
    if question_ids:
        statement = statement.where(Question.id.in_(question_ids))
    if not force:
        statement = statement.where(Question.score.is_(None))
    if limit is not None:
        statement = statement.limit(max(0, limit))
    return list(db.exec(statement))


def get_question_context(db, question_id: int) -> str:
    from sqlmodel import select

    from app.db.models import QuestionTranscriptMap, Transcript

    statement = (
        select(Transcript)
        .join(
            QuestionTranscriptMap,
            QuestionTranscriptMap.transcript_id == Transcript.id,
        )
        .where(QuestionTranscriptMap.question_id == question_id)
        .order_by(
            Transcript.__table__.c.start_time.asc().nulls_last(),
            Transcript.__table__.c.seq.asc().nulls_last(),
            Transcript.__table__.c.id.asc(),
        )
    )
    transcripts = list(db.exec(statement))
    return "\n".join(t.text.strip() for t in transcripts if t.text and t.text.strip())


def get_question_ids(questions: list) -> list[int]:
    return [question.id for question in questions if question.id is not None]


def load_evaluate_question_quality() -> Callable[[str, str], str]:
    module_path = BACKEND_DIR / "app" / "services" / "llm.py"
    spec = importlib.util.spec_from_file_location("_openclass_llm", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"无法加载 LLM 服务模块: {module_path}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.evaluate_question_quality


def parse_quality_score(raw_result: str) -> float:
    payload = parse_quality_payload(raw_result)
    score = payload.get("score")
    if not isinstance(score, (int, float)):
        raise ValueError("评分 JSON 缺少数字 score 字段")

    reported_score = float(score)
    calculated_score = calculate_quality_score_from_dimensions(payload)
    if calculated_score is None:
        normalized_score = apply_fatal_dimension(reported_score, payload)
    else:
        normalized_score = calculated_score
        if abs(reported_score - calculated_score) > 0.02:
            logger.warning(
                "LLM 问题评分总分与维度不一致: reported=%.3f calculated=%.3f；以维度重算分为准",
                reported_score,
                calculated_score,
            )
    normalized_score = max(-1.0, min(1.0, normalized_score))
    return float(
        Decimal(str(normalized_score)).quantize(
            Decimal("0.001"), rounding=ROUND_HALF_UP
        )
    )


def calculate_quality_score_from_dimensions(payload: dict[str, Any]) -> float | None:
    dimensions = payload.get("dimensions")
    if not isinstance(dimensions, dict):
        return None

    fatal = dimensions.get("fatal")
    if not isinstance(fatal, (int, float)):
        return None
    fatal_score = -1.0 if float(fatal) < 0 else 0.0

    base_score = 0.0
    for dimension_name, weight in QUESTION_QUALITY_DIMENSION_WEIGHTS.items():
        dimension_score = dimensions.get(dimension_name)
        if not isinstance(dimension_score, (int, float)):
            return None
        clamped_dimension_score = max(0.0, min(1.0, float(dimension_score)))
        base_score += weight * clamped_dimension_score

    return base_score + fatal_score


def apply_fatal_dimension(score: float, payload: dict[str, Any]) -> float:
    dimensions = payload.get("dimensions")
    if not isinstance(dimensions, dict):
        return score

    fatal = dimensions.get("fatal")
    if not isinstance(fatal, (int, float)) or fatal >= 0:
        return score

    if score < 0:
        return score

    return score + max(-1.0, float(fatal))


def parse_quality_payload(raw_result: str) -> dict[str, Any]:
    if not isinstance(raw_result, str) or not raw_result.strip():
        raise ValueError("评分结果为空")

    text = raw_result.strip()
    candidates = [text]

    if text.startswith("```"):
        stripped = text.strip("`").strip()
        if stripped.lower().startswith("json"):
            stripped = stripped[4:].strip()
        candidates.append(stripped)

    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and start < end:
        candidates.append(text[start : end + 1])

    last_error: Exception | None = None
    for candidate in candidates:
        try:
            payload = json.loads(candidate)
            if isinstance(payload, dict):
                return payload
        except json.JSONDecodeError as exc:
            last_error = exc

    raise ValueError(f"无法解析评分 JSON: {last_error}")


def score_question(
    question_id: int,
    *,
    args: argparse.Namespace,
    evaluate_question_quality: Callable[[str, str], str],
    engine,
) -> tuple[str, int, float | None, str | None]:
    from sqlmodel import Session

    from app.db.models import Question

    with Session(engine) as db:
        question = db.get(Question, question_id)
        if question is None:
            return "skipped", question_id, None, "问题不存在"

        if not args.force and question.score is not None:
            return "skipped", question_id, question.score, "问题已有 score"

        context = get_question_context(db, question_id)
        if not context:
            message = "没有关联讲解内容"
            if args.skip_missing_context:
                return "skipped", question_id, None, message
            return "failed", question_id, None, message

        try:
            raw_result = evaluate_question_quality(question.text, context)
            score = parse_quality_score(raw_result)
        except Exception as exc:
            if args.default_on_failure is None:
                return "failed", question_id, None, str(exc)
            score = max(-1.0, min(1.0, float(args.default_on_failure)))
            logger.warning(
                "问题 %s 评分失败，写入默认 score %.3f: %s",
                question_id,
                score,
                exc,
            )

        old_score = question.score
        if not args.dry_run:
            question.score = score
            db.add(question)
            db.commit()
            db.refresh(question)

        logger.info(
            "问题 %s score: %s -> %.3f%s",
            question_id,
            old_score,
            score,
            " (dry-run)" if args.dry_run else "",
        )
        return "scored", question_id, score, None


def backfill_scores(args: argparse.Namespace) -> int:
    from sqlmodel import Session

    from app.db.session import get_engine

    evaluate_question_quality = load_evaluate_question_quality()
    worker_count = normalize_workers(args.workers)
    updated_count = 0
    skipped_count = 0
    failed_count = 0
    engine = get_engine()

    with Session(engine) as db:
        questions = list_target_questions(
            db,
            question_ids=args.question_id,
            force=args.force,
            limit=args.limit,
        )
        question_ids = get_question_ids(questions)

    logger.info("待处理问题数: %d，workers=%d", len(question_ids), worker_count)

    if worker_count == 1:
        results = [
            score_question(
                question_id,
                args=args,
                evaluate_question_quality=evaluate_question_quality,
                engine=engine,
            )
            for question_id in question_ids
        ]
    else:
        results = []
        with ThreadPoolExecutor(max_workers=worker_count) as executor:
            future_map = {
                executor.submit(
                    score_question,
                    question_id,
                    args=args,
                    evaluate_question_quality=evaluate_question_quality,
                    engine=engine,
                ): question_id
                for question_id in question_ids
            }
            for future in as_completed(future_map):
                question_id = future_map[future]
                try:
                    results.append(future.result())
                except Exception as exc:
                    logger.exception("问题 %s 处理线程异常: %s", question_id, exc)
                    results.append(("failed", question_id, None, str(exc)))

    for status, question_id, _score, message in results:
        if status == "scored":
            updated_count += 1
        elif status == "skipped":
            skipped_count += 1
            if message:
                logger.warning("问题 %s 已跳过: %s", question_id, message)
        else:
            failed_count += 1
            if message:
                logger.error("问题 %s 处理失败: %s", question_id, message)

    logger.info(
        "处理完成: scored=%d skipped=%d failed=%d dry_run=%s",
        updated_count,
        skipped_count,
        failed_count,
        args.dry_run,
    )
    return 1 if failed_count else 0


def main() -> int:
    args = parse_args()
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    return backfill_scores(args)


if __name__ == "__main__":
    raise SystemExit(main())
