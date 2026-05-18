"""关键词模型下载策略与缓存检查。"""

from __future__ import annotations

import logging
import os
import sys
import time
from dataclasses import dataclass
from typing import Iterable

from huggingface_hub import scan_cache_dir
from huggingface_hub.constants import HF_HUB_CACHE


logger = logging.getLogger(__name__)

KEYWORD_MODEL_REPOS = (
    "shibing624/text2vec-base-chinese",
    "sentence-transformers/all-MiniLM-L6-v2",
)

_keyword_model_download_allowed = False


@dataclass(frozen=True)
class KeywordModelCacheEntry:
    """单个关键词模型缓存信息。"""

    repo_id: str
    cached: bool
    repo_path: str | None = None
    snapshot_path: str | None = None
    commit_hash: str | None = None
    size_on_disk: int | None = None
    nb_files: int | None = None


def get_keyword_model_download_allowed() -> bool:
    """获取当前关键词模型是否允许联网下载。"""
    return _keyword_model_download_allowed


def set_keyword_model_download_allowed(allowed: bool) -> None:
    """设置当前关键词模型是否允许联网下载。"""
    global _keyword_model_download_allowed
    _keyword_model_download_allowed = bool(allowed)


def describe_keyword_model_cache() -> list[KeywordModelCacheEntry]:
    """扫描并返回关键词模型缓存信息。"""
    cache_info = scan_cache_dir()
    repo_map = {repo.repo_id: repo for repo in cache_info.repos}

    if cache_info.warnings:
        for warning in cache_info.warnings:
            logger.warning("Hugging Face 缓存扫描警告: %s", warning)

    entries: list[KeywordModelCacheEntry] = []
    logger.info("Hugging Face 缓存目录: %s", HF_HUB_CACHE)
    logger.info("Hugging Face 缓存总大小: %.2f MB", cache_info.size_on_disk / 1024 / 1024)

    for repo_id in KEYWORD_MODEL_REPOS:
        repo = repo_map.get(repo_id)
        if repo is None:
            entry = KeywordModelCacheEntry(repo_id=repo_id, cached=False)
            entries.append(entry)
            logger.warning("模型缓存未找到: %s", repo_id)
            continue

        revision = _pick_revision(repo.revisions)
        entry = KeywordModelCacheEntry(
            repo_id=repo.repo_id,
            cached=True,
            repo_path=str(repo.repo_path),
            snapshot_path=str(revision.snapshot_path) if revision else None,
            commit_hash=revision.commit_hash if revision else None,
            size_on_disk=repo.size_on_disk,
            nb_files=repo.nb_files,
        )
        entries.append(entry)
        logger.info(
            "模型缓存已找到: %s | 路径: %s | snapshot: %s | 版本: %s | 文件数: %s | 大小: %.2f MB",
            repo.repo_id,
            repo.repo_path,
            entry.snapshot_path,
            entry.commit_hash,
            repo.nb_files,
            repo.size_on_disk / 1024 / 1024,
        )

    return entries


def prepare_keyword_model_download_policy(timeout_seconds: float = 5.0) -> bool:
    """在启动阶段决定关键词模型是否允许联网下载。"""
    entries = describe_keyword_model_cache()
    missing_entries = [entry for entry in entries if not entry.cached]

    if not missing_entries:
        logger.info("关键词模型缓存完整，启动时使用本地模型，不提示联网下载")
        set_keyword_model_download_allowed(False)
        return False

    missing_models = ", ".join(entry.repo_id for entry in missing_entries)
    logger.warning("关键词模型缓存不完整，缺失模型: %s", missing_models)

    if not sys.stdin.isatty() or not sys.stdout.isatty():
        logger.info("当前不是交互终端，默认不联网下载关键词模型")
        set_keyword_model_download_allowed(False)
        return False

    prompt = (
        "检测到关键词模型缓存不完整，是否允许联网下载？"
        "输入 y 允许下载，输入 n 或 5 秒内无输入则仅使用本地缓存："
    )
    answer = _read_input_with_timeout(prompt, timeout_seconds)
    allowed = isinstance(answer, str) and answer.strip().lower().startswith("y")
    set_keyword_model_download_allowed(allowed)

    if allowed:
        logger.info("已选择允许联网下载关键词模型")
    else:
        logger.info("已选择仅使用本地模型，不联网下载")
    return allowed


def _pick_revision(revisions: Iterable[object]):
    """从缓存修订版本中选择最新的一份。"""
    revision_list = list(revisions)
    if not revision_list:
        return None
    return max(revision_list, key=lambda item: getattr(item, "last_modified", 0))


def _read_input_with_timeout(prompt: str, timeout_seconds: float) -> str | None:
    """读取一行输入，超时返回 None。"""
    print(prompt, end="", flush=True)

    if timeout_seconds <= 0:
        print()
        return None

    deadline = time.monotonic() + timeout_seconds
    if os.name == "nt":
        return _read_input_with_timeout_windows(deadline)
    return _read_input_with_timeout_posix(deadline)


def _read_input_with_timeout_windows(deadline: float) -> str | None:
    """Windows 下按键轮询读取输入。"""
    import msvcrt

    chars: list[str] = []
    while time.monotonic() < deadline:
        if msvcrt.kbhit():
            ch = msvcrt.getwch()
            if ch in ("\r", "\n"):
                print()
                return "".join(chars)
            if ch == "\b":
                if chars:
                    chars.pop()
                    sys.stdout.write("\b \b")
                    sys.stdout.flush()
                continue
            chars.append(ch)
            sys.stdout.write(ch)
            sys.stdout.flush()
        time.sleep(0.05)

    print()
    return None


def _read_input_with_timeout_posix(deadline: float) -> str | None:
    """POSIX 下使用 select 读取输入。"""
    import select

    remaining = max(0.0, deadline - time.monotonic())
    ready, _, _ = select.select([sys.stdin], [], [], remaining)
    if not ready:
        print()
        return None

    line = sys.stdin.readline()
    return line.rstrip("\r\n")
