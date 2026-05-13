from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = PROJECT_ROOT / "backend"
sys.path.insert(0, str(BACKEND_ROOT))

from app.config_defaults import (
    DEFAULT_DATABASE_URL,
    DEFAULT_SETTINGS_VALUES,
    SENSITIVE_SETTING_KEYS,
)
from app.db.config_store import _coerce_value, _parse_value


SQLITE_URL_PREFIX = "sqlite:///"
SECRET_KEY_PARTS = (
    "api_key",
    "apikey",
    "access_key",
    "accesskey",
    "secret",
    "token",
    "password",
    "passwd",
    "credential",
    "private_key",
    "privatekey",
    "client_secret",
    "clientsecret",
    "refresh_token",
    "refreshtoken",
    "access_token",
    "accesstoken",
    "id_token",
    "idtoken",
    "auth_token",
    "authtoken",
    "bearer",
    "authorization",
    "signing_secret",
    "signingsecret",
    "webhook_secret",
    "webhooksecret",
)
SECRET_KEY_PATTERNS = (
    re.compile(r"api.*key"),
    re.compile(r"key.*api"),
    re.compile(r"access.*key"),
    re.compile(r"secret.*key"),
    re.compile(r"private.*key"),
    re.compile(r"client.*secret"),
    re.compile(r"refresh.*token"),
    re.compile(r"access.*token"),
    re.compile(r"auth.*token"),
    re.compile(r"id.*token"),
    re.compile(r"signing.*secret"),
    re.compile(r"webhook.*secret"),
)
INLINE_SECRET_PATTERN = re.compile(
    r"(?i)(api[_-]?key|access[_-]?key|secret|token|password|passwd|credential)"
    r"(\s*[:=]\s*)"
    r"([^\s,;&\"'}]+)"
)
URL_CREDENTIAL_PATTERN = re.compile(r"(?i)(://[^/\s:@]+:)([^@\s/]+)(@)")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Compare app.config_defaults.DEFAULT_SETTINGS_VALUES with the "
            "settings table in a SQLite database without exposing secrets."
        )
    )
    parser.add_argument(
        "--database",
        "-d",
        default=DEFAULT_DATABASE_URL,
        help=(
            "SQLite database path or sqlite:/// URL. Defaults to the project's "
            "DEFAULT_DATABASE_URL."
        ),
    )
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Output format.",
    )
    parser.add_argument(
        "--full-values",
        action="store_true",
        help="Print full non-sensitive values instead of truncating them.",
    )
    parser.add_argument(
        "--max-value-length",
        type=int,
        default=80,
        help="Maximum length for each non-sensitive value unless --full-values is set.",
    )
    parser.add_argument(
        "--multiline",
        action="store_true",
        help="Preserve newlines in non-sensitive values. By default values are printed as one-line previews.",
    )
    parser.add_argument(
        "--include-extra",
        action="store_true",
        help="Also list settings that exist only in the database.",
    )
    return parser.parse_args()


def resolve_sqlite_path(database: str) -> Path:
    raw_path = database
    if database.startswith(SQLITE_URL_PREFIX):
        raw_path = database[len(SQLITE_URL_PREFIX) :]

    if raw_path == ":memory:":
        raise ValueError("In-memory SQLite databases cannot be inspected by this script.")

    path = Path(raw_path)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path.resolve()


def load_db_settings(db_path: Path) -> dict[str, str]:
    if not db_path.exists():
        raise FileNotFoundError(f"Database file does not exist: {db_path}")

    try:
        with sqlite3.connect(db_path) as conn:
            rows = conn.execute("SELECT key, value FROM settings").fetchall()
    except sqlite3.OperationalError as exc:
        raise RuntimeError(f"Failed to read settings table from {db_path}: {exc}") from exc

    return {str(key): "" if value is None else str(value) for key, value in rows}


def is_sensitive_key(key: str) -> bool:
    normalized = key.lower()
    compact = re.sub(r"[^a-z0-9]", "", normalized)
    return (
        key in SENSITIVE_SETTING_KEYS
        or any(part in normalized or part in compact for part in SECRET_KEY_PARTS)
        or any(pattern.search(normalized) or pattern.search(compact) for pattern in SECRET_KEY_PATTERNS)
    )


def parse_db_value(key: str, raw_value: str) -> Any:
    if key not in DEFAULT_SETTINGS_VALUES:
        return raw_value
    return _parse_value(key, raw_value)


def values_are_equal(key: str, default_value: Any, raw_db_value: str) -> bool:
    if key in DEFAULT_SETTINGS_VALUES:
        return _parse_value(key, raw_db_value) == default_value
    return _coerce_value(key, default_value) == raw_db_value


def display_value(key: str, value: Any, *, full_values: bool, max_length: int) -> str:
    if is_sensitive_key(key):
        return "[secret hidden]"

    text = json.dumps(value, ensure_ascii=False) if not isinstance(value, str) else value
    text = redact_inline_secrets(text)
    if full_values or max_length < 0 or len(text) <= max_length:
        return text
    return text[:max_length] + f"... [truncated, {len(text)} chars total]"


def redact_inline_secrets(text: str) -> str:
    text = URL_CREDENTIAL_PATTERN.sub(r"\1[secret hidden]\3", text)
    return INLINE_SECRET_PATTERN.sub(r"\1\2[secret hidden]", text)


def normalize_preview(value: str, *, multiline: bool) -> str:
    if multiline:
        return value
    return value.replace("\\", "\\\\").replace("\r", "\\r").replace("\n", "\\n")


def render_value(
    key: str,
    value: Any,
    *,
    full_values: bool,
    max_length: int,
    multiline: bool,
) -> str:
    return normalize_preview(
        display_value(
            key,
            value,
            full_values=full_values,
            max_length=max_length,
        ),
        multiline=multiline,
    )


def build_diff(
    db_settings: dict[str, str],
    *,
    full_values: bool,
    max_value_length: int,
    include_extra: bool,
    multiline: bool,
) -> list[dict[str, Any]]:
    diffs: list[dict[str, Any]] = []

    for key, default_value in DEFAULT_SETTINGS_VALUES.items():
        if key not in db_settings:
            diffs.append(
                {
                    "key": key,
                    "status": "missing_in_database",
                    "default": render_value(
                        key,
                        default_value,
                        full_values=full_values,
                        max_length=max_value_length,
                        multiline=multiline,
                    ),
                    "database": "[missing]",
                }
            )
            continue

        raw_db_value = db_settings[key]
        if values_are_equal(key, default_value, raw_db_value):
            continue

        parsed_db_value = parse_db_value(key, raw_db_value)
        diffs.append(
            {
                "key": key,
                "status": "different",
                "default": render_value(
                    key,
                    default_value,
                    full_values=full_values,
                    max_length=max_value_length,
                    multiline=multiline,
                ),
                "database": render_value(
                    key,
                    parsed_db_value,
                    full_values=full_values,
                    max_length=max_value_length,
                    multiline=multiline,
                ),
            }
        )

    if include_extra:
        for key in sorted(set(db_settings) - set(DEFAULT_SETTINGS_VALUES)):
            diffs.append(
                {
                    "key": key,
                    "status": "only_in_database",
                    "default": "[missing]",
                    "database": render_value(
                        key,
                        db_settings[key],
                        full_values=full_values,
                        max_length=max_value_length,
                        multiline=multiline,
                    ),
                }
            )

    return diffs


def print_text(diffs: list[dict[str, Any]], db_path: Path) -> None:
    print(f"Database: {db_path}")
    print(f"Different or missing settings: {len(diffs)}")

    if not diffs:
        print("No differences found.")
        return

    for item in diffs:
        print()
        print(f"- {item['key']} ({item['status']})")
        print(f"  default : {item['default']}")
        print(f"  database: {item['database']}")


def main() -> int:
    args = parse_args()

    try:
        db_path = resolve_sqlite_path(args.database)
        db_settings = load_db_settings(db_path)
        diffs = build_diff(
            db_settings,
            full_values=args.full_values,
            max_value_length=args.max_value_length,
            include_extra=args.include_extra,
            multiline=args.multiline,
        )
    except (FileNotFoundError, RuntimeError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    if args.format == "json":
        print(json.dumps({"database": str(db_path), "diffs": diffs}, ensure_ascii=False, indent=2))
    else:
        print_text(diffs, db_path)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
