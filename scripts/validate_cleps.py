"""Validate proposal names, locations, and YAML front matter."""
from datetime import date
from pathlib import Path
import re
import sys

import yaml

PROPOSALS_DIR = Path("proposals")
FILENAME_RE = re.compile(r"^clep-(\d{4})(?:-[a-z0-9]+(?:-[a-z0-9]+)*)?\.md$")
REQUIRED_FIELDS = {"clep", "title", "author", "status", "type", "created", "requires"}
VALID_STATUSES = {"Draft", "Proposed", "Accepted", "Rejected", "Implemented", "Deferred"}
VALID_TYPES = {"Standards Track", "Informational", "Process"}
STATUS_DIRS = {
    "Draft": "", "Proposed": "proposed", "Accepted": "accepted",
    "Rejected": "rejected", "Implemented": "implemented", "Deferred": "deferred",
}


def validate_file(path: Path, seen_ids: set[int]) -> list[str]:
    errors: list[str] = []
    match = FILENAME_RE.fullmatch(path.name)
    if not match:
        return [f"Filename must match clep-XXXX.md or clep-XXXX-title-slug.md: {path.as_posix()}"]
    filename_id = int(match.group(1))
    if filename_id in seen_ids:
        errors.append(f"Duplicate CLEP id {filename_id:04d}")
    seen_ids.add(filename_id)

    content = path.read_text(encoding="utf-8")
    front_matter = re.match(r"^---\s*\n(.*?)\n---\s*(?:\n|$)", content, re.DOTALL)
    if not front_matter:
        return errors + ["Missing or malformed YAML front matter"]
    try:
        metadata = yaml.safe_load(front_matter.group(1))
    except yaml.YAMLError as exc:
        return errors + [f"Invalid YAML: {exc}"]
    if not isinstance(metadata, dict):
        return errors + ["Front matter must be a YAML mapping"]

    missing = REQUIRED_FIELDS - metadata.keys()
    if missing:
        errors.append(f"Missing required fields: {', '.join(sorted(missing))}")
    if metadata.get("clep") != filename_id:
        errors.append(f"clep must match filename id {filename_id:04d}")
    status = metadata.get("status")
    if status not in VALID_STATUSES:
        errors.append(f"Invalid status {status!r}; allowed: {', '.join(sorted(VALID_STATUSES))}")
    else:
        # Drafts live at the proposals root; every other status has its own folder.
        expected = PROPOSALS_DIR / STATUS_DIRS[status] if STATUS_DIRS[status] else PROPOSALS_DIR
        if path.parent != expected:
            errors.append(f"Status {status} proposals must be in {expected.as_posix()}/")
    if metadata.get("type") not in VALID_TYPES:
        errors.append(f"Invalid type {metadata.get('type')!r}; allowed: {', '.join(sorted(VALID_TYPES))}")
    if not isinstance(metadata.get("title"), str) or not metadata["title"].strip():
        errors.append("title must be a non-empty string")
    if not isinstance(metadata.get("author"), str) or not metadata["author"].strip():
        errors.append("author must be a non-empty string")
    created = metadata.get("created")
    if not (isinstance(created, date) or isinstance(created, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", created)):
        errors.append("created must use YYYY-MM-DD format")
    requires = metadata.get("requires")
    if not isinstance(requires, list) or any(type(item) is not int or item < 0 for item in requires):
        errors.append("requires must be a list of non-negative CLEP numbers (use [] when there are no dependencies)")
    elif filename_id in requires:
        errors.append("A CLEP cannot require itself")
    return errors


def main() -> int:
    # An empty repository may not have the folder yet; that is a valid state.
    files = sorted(PROPOSALS_DIR.rglob("*.md")) if PROPOSALS_DIR.is_dir() else []
    seen: set[int] = set()
    failures = 0
    dependencies: dict[int, list[int]] = {}
    for path in files:
        errors = validate_file(path, seen)
        match = FILENAME_RE.fullmatch(path.name)
        if match:
            try:
                content = path.read_text(encoding="utf-8")
                front_matter = re.match(r"^---\s*\n(.*?)\n---\s*(?:\n|$)", content, re.DOTALL)
                metadata = yaml.safe_load(front_matter.group(1)) if front_matter else {}
                if isinstance(metadata, dict) and isinstance(metadata.get("requires"), list):
                    dependencies[int(match.group(1))] = metadata["requires"]
            except (OSError, yaml.YAMLError):
                pass
        if errors:
            print(f"FAIL {path.as_posix()}")
            for error in errors:
                print(f"  - {error}")
            failures += len(errors)
        else:
            print(f"PASS {path.as_posix()}")
    for clep_id, required_ids in dependencies.items():
        for required_id in required_ids:
            if type(required_id) is int and required_id not in seen:
                print(f"FAIL CLEP-{clep_id:04d}: requires unknown CLEP-{required_id:04d}")
                failures += 1
    if failures:
        print(f"Validation failed with {failures} error(s).")
        return 1
    print(f"All {len(files)} proposal(s) passed validation.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
