"""
Case Memory Service — Intelligence Flywheel

When a task is completed (status → "done"), this service archives it as a
searchable case study on disk. Each case study has:

  backend/case_studies/MMDD_task-slug/
  ├── README.md       # Human-readable summary
  ├── metadata.json   # Structured data for indexing
  └── artifacts/      # Empty dir for future attachments

The slug is derived from the task title, date-prefixed for chronological order.
"""

import os
import re
import json
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

CASE_STUDIES_DIR = Path(__file__).parent.parent / "case_studies"


def slugify(text: str, max_length: int = 50) -> str:
    """Convert text to a filesystem-safe slug."""
    slug = text.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    slug = slug.strip("-")
    return slug[:max_length]


async def create_case_study(task_data: dict) -> dict:
    """Create a case study directory from a completed task.

    Args:
        task_data: Dict with keys: id, title, description, notes, assignee,
                   value_stream, start_date, due_date, created_at, comments

    Returns:
        {"case_dir": str, "slug": str}
    """
    now = datetime.utcnow()
    date_prefix = now.strftime("%m%d")
    title_slug = slugify(task_data.get("title", "untitled"))
    slug = f"{date_prefix}_{title_slug}"

    case_dir = CASE_STUDIES_DIR / slug
    case_dir.mkdir(parents=True, exist_ok=True)
    (case_dir / "artifacts").mkdir(exist_ok=True)

    # Build README.md
    title = task_data.get("title", "Untitled Task")
    description = task_data.get("description") or ""
    notes = task_data.get("notes") or ""
    assignee = task_data.get("assignee") or "Unknown"
    value_stream = task_data.get("value_stream") or "None"
    start_date = task_data.get("start_date") or "N/A"
    due_date = task_data.get("due_date") or "N/A"
    created_at = task_data.get("created_at") or "N/A"
    comments = task_data.get("comments") or []

    readme_lines = [
        f"# {title}",
        "",
        f"**Assignee:** {assignee}",
        f"**Value Stream:** {value_stream}",
        f"**Created:** {created_at}",
        f"**Started:** {start_date}",
        f"**Due:** {due_date}",
        f"**Completed:** {now.isoformat()}",
        "",
    ]

    if description:
        readme_lines += ["## Description", "", description, ""]

    if notes:
        readme_lines += ["## Notes", "", notes, ""]

    if comments:
        readme_lines += ["## Discussion", ""]
        for c in comments:
            readme_lines.append(f"- **{c.get('author', 'Unknown')}:** {c.get('text', '')}")
        readme_lines.append("")

    readme_path = case_dir / "README.md"
    readme_path.write_text("\n".join(readme_lines), encoding="utf-8")

    # Build metadata.json
    metadata = {
        "id": task_data.get("id"),
        "title": title,
        "slug": slug,
        "description": description,
        "notes": notes,
        "assignee": assignee,
        "value_stream": value_stream,
        "start_date": start_date,
        "due_date": due_date,
        "created_at": created_at,
        "completed_at": now.isoformat(),
        "comment_count": len(comments),
        "indexed_text": f"{title} {description} {notes}".strip(),
    }

    metadata_path = case_dir / "metadata.json"
    metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    logger.info(f"Case study created: {slug}")

    # Auto-index in RAG if available
    try:
        from services.semantic_rag import get_rag_service
        rag = get_rag_service()
        rag.add_to_index(str(case_dir))
    except Exception as e:
        logger.warning(f"RAG indexing skipped for {slug}: {e}")

    return {"case_dir": str(case_dir), "slug": slug}
