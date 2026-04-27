from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SELF_PATH = Path(__file__).resolve()
DEFAULT_EXTENSIONS = {
    ".md",
    ".py",
    ".html",
    ".css",
    ".js",
    ".json",
    ".yaml",
    ".yml",
    ".toml",
    ".txt",
}
SKIP_PARTS = {".git", ".venv", "__pycache__", "staticfiles"}
MOJIBAKE_MARKERS = ("隞", "嚗", "蝯", "鍂", "銝", "�")


def should_skip(path: Path) -> bool:
    return any(part in SKIP_PARTS for part in path.parts)


def iter_text_files(root: Path) -> list[Path]:
    return sorted(
        path
        for path in root.rglob("*")
        if path.is_file() and path.suffix.lower() in DEFAULT_EXTENSIONS and not should_skip(path)
    )


def analyze_file(path: Path) -> dict[str, object]:
    record: dict[str, object] = {
        "path": str(path.relative_to(ROOT)).replace("\\", "/"),
        "utf8_ok": False,
        "bom": False,
        "replacement_char_count": 0,
        "mojibake_marker_counts": {},
    }

    raw = path.read_bytes()
    record["bom"] = raw.startswith(b"\xef\xbb\xbf")

    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        record["error"] = f"{type(exc).__name__}: {exc}"
        return record

    record["utf8_ok"] = True
    record["replacement_char_count"] = text.count("\ufffd")
    if path.resolve() == SELF_PATH:
        marker_counts = {}
        record["replacement_char_count"] = 0
    else:
        marker_counts = {marker: text.count(marker) for marker in MOJIBAKE_MARKERS if text.count(marker)}
    record["mojibake_marker_counts"] = marker_counts
    return record


def preview_file(path: Path, limit: int) -> dict[str, object]:
    text = path.read_text(encoding="utf-8")
    preview = text[:limit]
    return {
        "path": str(path.relative_to(ROOT)).replace("\\", "/"),
        "preview_unicode_escape": preview.encode("unicode_escape").decode("ascii"),
    }


def build_summary(records: list[dict[str, object]]) -> dict[str, object]:
    decode_errors = [record for record in records if not record["utf8_ok"]]
    suspicious = [
        record
        for record in records
        if record["utf8_ok"]
        and (
            record["replacement_char_count"]  # type: ignore[truthy-bool]
            or record["mojibake_marker_counts"]  # type: ignore[truthy-bool]
        )
    ]
    bom_files = [record["path"] for record in records if record["bom"]]
    return {
        "root": str(ROOT),
        "scanned_file_count": len(records),
        "decode_error_count": len(decode_errors),
        "suspicious_file_count": len(suspicious),
        "bom_file_count": len(bom_files),
        "decode_errors": decode_errors,
        "suspicious_files": suspicious,
        "bom_files": bom_files,
        "note": "Output is ASCII-safe JSON so it can be read even when the terminal code page is not UTF-8.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Scan repository text files for UTF-8 decoding issues and suspicious mojibake markers."
    )
    parser.add_argument(
        "--preview",
        metavar="PATH",
        help="Preview one UTF-8 text file using unicode_escape output to avoid terminal encoding issues.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=1200,
        help="Character limit for --preview output. Default: 1200.",
    )
    args = parser.parse_args()

    if args.preview:
        payload = preview_file(ROOT / args.preview, args.limit)
    else:
        payload = build_summary([analyze_file(path) for path in iter_text_files(ROOT)])

    print(json.dumps(payload, indent=2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
