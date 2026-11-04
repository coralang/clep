"""Assign IDs to new proposals and file proposals by their current status."""
from pathlib import Path
import re
import sys

import yaml

ROOT = Path("proposals")
FILENAME_RE = re.compile(r"^clep-(\d{4})(?:-[a-z0-9]+(?:-[a-z0-9]+)*)?\.md$")
STATUS_DIRS = {
    "Draft": None, "Proposed": "proposed", "Accepted": "accepted",
    "Rejected": "rejected", "Implemented": "implemented", "Deferred": "deferred",
}


def read_front_matter(path: Path) -> tuple[dict, str] | None:
    content = path.read_text(encoding="utf-8")
    match = re.match(r"^---[ \t]*\r?\n(.*?)\r?\n---[ \t]*(?:\r?\n|$)", content, re.DOTALL)
    if not match:
        return None
    metadata = yaml.safe_load(match.group(1))
    if not isinstance(metadata, dict):
        return None
    return metadata, content[match.end():]


def title_slug(title: object) -> str:
    return re.sub(r"[^a-z0-9]+", "-", str(title).lower()).strip("-")


def proposal_filename(clep_id: int, title: object) -> str:
    slug = title_slug(title)
    return f"clep-{clep_id:04d}{'-' + slug if slug else ''}.md"


def main() -> int:
    if not ROOT.is_dir():
        print("No proposals directory found; nothing to prepare.")
        return 0
    files = sorted(ROOT.glob("*.md"))
    used = {int(match.group(1)) for p in ROOT.rglob("clep-*.md") if (match := FILENAME_RE.fullmatch(p.name))}
    next_id = max(used, default=0) + 1

    # New drafts use clep: null. IDs are allocated in filename order.
    for path in files:
        parsed = read_front_matter(path)
        if not parsed:
            continue
        metadata, tail = parsed
        if metadata.get("clep") is not None:
            continue
        if metadata.get("status", "Draft") != "Draft":
            print(f"Cannot assign an id to non-Draft proposal: {path}")
            return 1
        metadata["clep"] = next_id
        new_name = ROOT / proposal_filename(next_id, metadata.get("title", ""))
        if new_name.exists() and new_name != path:
            print(f"Refusing to overwrite {new_name}")
            return 1
        rendered = "---\n" + yaml.safe_dump(metadata, sort_keys=False, allow_unicode=True).rstrip() + "\n---\n\n" + tail.lstrip("\n")
        path.unlink()
        new_name.write_text(rendered, encoding="utf-8")
        used.add(next_id)
        print(f"Assigned CLEP-{next_id:04d} to {new_name.as_posix()}")
        next_id += 1

    # Relocate files after IDs have been allocated. Re-scan so renames are included.
    for path in sorted(ROOT.rglob("*.md")):
        parsed = read_front_matter(path)
        if not parsed:
            continue
        metadata, _ = parsed
        folder = STATUS_DIRS.get(metadata.get("status"))
        if metadata.get("status") not in STATUS_DIRS:
            continue  # The validator reports unsupported statuses.
        destination_dir = ROOT / folder if folder else ROOT
        destination = destination_dir / path.name
        if destination == path:
            continue
        destination_dir.mkdir(parents=True, exist_ok=True)
        if destination.exists():
            print(f"Refusing to overwrite {destination}")
            return 1
        path.rename(destination)
        print(f"Moved {path.as_posix()} to {destination.as_posix()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
