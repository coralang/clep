"""Build the status-grouped proposal directory in README.md."""
from pathlib import Path
import re

import yaml

PROPOSALS_DIR = Path("proposals")
README_PATH = Path("README.md")
START_MARKER = "<!-- CLEPS-LIST:START -->"
END_MARKER = "<!-- CLEPS-LIST:END -->"
STATUSES = ["Draft", "Proposed", "Accepted", "Deferred", "Rejected", "Implemented"]


def proposals() -> list[tuple[Path, dict]]:
    items = []
    for path in PROPOSALS_DIR.rglob("*.md"):
        content = path.read_text(encoding="utf-8")
        match = re.match(r"^---\s*\n(.*?)\n---\s*(?:\n|$)", content, re.DOTALL)
        if not match:
            continue
        try:
            data = yaml.safe_load(match.group(1))
        except yaml.YAMLError:
            continue
        if isinstance(data, dict):
            items.append((path, data))
    return sorted(items, key=lambda item: item[1].get("clep", 0))


def render() -> str:
    items = proposals()
    if not items:
        return "\n*No enhancement proposals registered yet.*\n"
    sections = ["", "### Table of contents", ""]
    for status in STATUSES:
        selected = [(path, meta) for path, meta in items if meta.get("status") == status]
        if selected:
            sections.append(f"- [{status}](#{status.lower()})")
            for path, meta in selected:
                clep = int(meta["clep"])
                title = str(meta.get("title", "Untitled")).replace("|", "\\|")
                sections.append(f"  - [CLEP-{clep:04d}: {title}]({path.as_posix()})")
    sections.append("")
    for status in STATUSES:
        selected = [(path, meta) for path, meta in items if meta.get("status") == status]
        if not selected:
            continue
        sections.extend([f"### {status}", "", "| CLEP | Title | Type | Author | Requires |", "| :--- | :--- | :--- | :--- | :--- |"])
        for path, meta in selected:
            clep = int(meta["clep"])
            title = str(meta.get("title", "Untitled")).replace("|", "\\|")
            author = re.sub(r"\s*<.*?>", "", str(meta.get("author", "Unknown"))).replace("|", "\\|")
            requires = meta.get("requires", [])
            dependency_text = ", ".join(f"CLEP-{number:04d}" for number in requires) if requires else "—"
            sections.append(f"| CLEP-{clep:04d} | [{title}]({path.as_posix()}) | {meta.get('type', '')} | {author} | {dependency_text} |")
        sections.append("")
    return "\n".join(sections)


def main() -> int:
    content = README_PATH.read_text(encoding="utf-8")
    pattern = re.compile(re.escape(START_MARKER) + r".*?" + re.escape(END_MARKER), re.DOTALL)
    if not pattern.search(content):
        print(f"Missing {START_MARKER} / {END_MARKER} markers in {README_PATH}")
        return 1
    updated = pattern.sub(lambda _: f"{START_MARKER}{render()}{END_MARKER}", content, count=1)
    README_PATH.write_text(updated, encoding="utf-8")
    print("README.md proposal directory updated.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
