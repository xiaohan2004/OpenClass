"""关键词模型下载策略测试。"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

TESTS_DIR = Path(__file__).parent
PROJECT_ROOT = TESTS_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.utils.model_download_policy import (
    KeywordModelCacheEntry,
    get_keyword_model_download_allowed,
    prepare_keyword_model_download_policy,
    set_keyword_model_download_allowed,
)


class TestKeywordModelDownloadPolicy(unittest.TestCase):
    def tearDown(self):
        set_keyword_model_download_allowed(False)

    def test_cached_models_skip_prompt(self):
        entries = [
            KeywordModelCacheEntry(
                repo_id="shibing624/text2vec-base-chinese",
                cached=True,
                repo_path="cache/a",
                snapshot_path="cache/a/snapshot",
                commit_hash="abc",
                size_on_disk=1,
                nb_files=1,
            ),
            KeywordModelCacheEntry(
                repo_id="sentence-transformers/all-MiniLM-L6-v2",
                cached=True,
                repo_path="cache/b",
                snapshot_path="cache/b/snapshot",
                commit_hash="def",
                size_on_disk=1,
                nb_files=1,
            ),
        ]

        with patch(
            "app.utils.model_download_policy.describe_keyword_model_cache",
            return_value=entries,
        ) as mock_describe, patch(
            "app.utils.model_download_policy._read_input_with_timeout"
        ) as mock_prompt:
            allowed = prepare_keyword_model_download_policy()

        self.assertFalse(allowed)
        self.assertFalse(get_keyword_model_download_allowed())
        mock_describe.assert_called_once()
        mock_prompt.assert_not_called()

    def test_missing_cache_allows_download_when_user_inputs_y(self):
        entries = [
            KeywordModelCacheEntry(
                repo_id="shibing624/text2vec-base-chinese",
                cached=False,
            ),
            KeywordModelCacheEntry(
                repo_id="sentence-transformers/all-MiniLM-L6-v2",
                cached=True,
                repo_path="cache/b",
                snapshot_path="cache/b/snapshot",
                commit_hash="def",
                size_on_disk=1,
                nb_files=1,
            ),
        ]

        with patch(
            "app.utils.model_download_policy.describe_keyword_model_cache",
            return_value=entries,
        ), patch(
            "app.utils.model_download_policy.sys.stdin.isatty",
            return_value=True,
        ), patch(
            "app.utils.model_download_policy.sys.stdout.isatty",
            return_value=True,
        ), patch(
            "app.utils.model_download_policy._read_input_with_timeout",
            return_value="y",
        ) as mock_prompt:
            allowed = prepare_keyword_model_download_policy()

        self.assertTrue(allowed)
        self.assertTrue(get_keyword_model_download_allowed())
        mock_prompt.assert_called_once()

    def test_missing_cache_defaults_to_local_only_without_tty(self):
        entries = [
            KeywordModelCacheEntry(
                repo_id="shibing624/text2vec-base-chinese",
                cached=False,
            ),
        ]

        with patch(
            "app.utils.model_download_policy.describe_keyword_model_cache",
            return_value=entries,
        ), patch(
            "app.utils.model_download_policy.sys.stdin.isatty",
            return_value=False,
        ), patch(
            "app.utils.model_download_policy.sys.stdout.isatty",
            return_value=False,
        ), patch(
            "app.utils.model_download_policy._read_input_with_timeout"
        ) as mock_prompt:
            allowed = prepare_keyword_model_download_policy()

        self.assertFalse(allowed)
        self.assertFalse(get_keyword_model_download_allowed())
        mock_prompt.assert_not_called()


if __name__ == "__main__":
    unittest.main()
