#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""
method-hoard CLI — manage a global hoard of proven, generalizable methods.

Storage: ~/.method-hoard/methods/*.md (markdown with YAML frontmatter)
Index:   ~/.method-hoard/index.db (SQLite FTS5, derived from files)

Usage:
    uv run hoard.py init
    uv run hoard.py stock          # reads method JSON from stdin
    uv run hoard.py search <query>
    uv run hoard.py get <id-or-slug>
    uv run hoard.py heuristic
    uv run hoard.py list
    uv run hoard.py update         # reads updated method JSON from stdin
    uv run hoard.py reindex
"""

import argparse
import json
import re
import shutil
import sqlite3
import sys
from datetime import date
from pathlib import Path

HOARD_DIR = Path.home() / ".method-hoard"
METHODS_DIR = HOARD_DIR / "methods"
INDEX_DB = HOARD_DIR / "index.db"

# Locate the seed directory relative to this script
SCRIPT_DIR = Path(__file__).resolve().parent
SEED_DIR = SCRIPT_DIR.parent / "seed"


# ---------------------------------------------------------------------------
# Markdown parsing
# ---------------------------------------------------------------------------

def parse_frontmatter(text: str) -> tuple[dict, str]:
    """Parse YAML frontmatter from markdown text. Returns (metadata, body)."""
    if not text.startswith("---"):
        return {}, text
    end = text.find("---", 3)
    if end == -1:
        return {}, text
    raw = text[3:end].strip()
    meta = {}
    for line in raw.splitlines():
        if ":" not in line:
            continue
        key, val = line.split(":", 1)
        key = key.strip()
        val = val.strip()
        # Handle YAML lists: [a, b, c]
        if val.startswith("[") and val.endswith("]"):
            val = [v.strip().strip("'\"") for v in val[1:-1].split(",") if v.strip()]
        elif val.isdigit():
            val = int(val)
        meta[key] = val
    body = text[end + 3:].strip()
    return meta, body


def render_frontmatter(meta: dict) -> str:
    """Render a dict as YAML frontmatter."""
    lines = ["---"]
    for k, v in meta.items():
        if isinstance(v, list):
            lines.append(f"{k}: [{', '.join(v)}]")
        else:
            lines.append(f"{k}: {v}")
    lines.append("---")
    return "\n".join(lines)


def extract_sections(body: str) -> dict[str, str]:
    """Extract ## sections from markdown body into a dict."""
    sections = {}
    current_key = None
    current_lines = []
    for line in body.splitlines():
        if line.startswith("## "):
            if current_key is not None:
                sections[current_key] = "\n".join(current_lines).strip()
            current_key = line[3:].strip().lower()
            current_lines = []
        else:
            current_lines.append(line)
    if current_key is not None:
        sections[current_key] = "\n".join(current_lines).strip()
    return sections


def read_method_file(path: Path) -> dict | None:
    """Read a method markdown file and return structured data."""
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None
    meta, body = parse_frontmatter(text)
    sections = extract_sections(body)
    return {
        "file_path": str(path),
        "file_name": path.name,
        **meta,
        "method_text": sections.get("method", ""),
        "code": sections.get("code", ""),
        "context": sections.get("context", ""),
        "raw_body": body,
    }


# ---------------------------------------------------------------------------
# Index management
# ---------------------------------------------------------------------------

def get_db() -> sqlite3.Connection:
    """Open (or create) the index database."""
    db = sqlite3.connect(str(INDEX_DB))
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA journal_mode=WAL")
    return db


def ensure_schema(db: sqlite3.Connection):
    """Create tables if they don't exist."""
    db.executescript("""
        CREATE TABLE IF NOT EXISTS methods (
            id INTEGER PRIMARY KEY,
            slug TEXT UNIQUE NOT NULL,
            file_path TEXT NOT NULL,
            title TEXT NOT NULL DEFAULT '',
            problem TEXT NOT NULL DEFAULT '',
            method_text TEXT NOT NULL DEFAULT '',
            code TEXT NOT NULL DEFAULT '',
            language TEXT NOT NULL DEFAULT '',
            tags TEXT NOT NULL DEFAULT '',
            source_project TEXT NOT NULL DEFAULT '',
            created TEXT NOT NULL DEFAULT '',
            updated TEXT NOT NULL DEFAULT '',
            retrievals INTEGER NOT NULL DEFAULT 0
        );
        CREATE VIRTUAL TABLE IF NOT EXISTS methods_fts USING fts5(
            slug, title, problem, method_text, code, tags, language,
            content='methods', content_rowid='id'
        );
        CREATE TRIGGER IF NOT EXISTS methods_ai AFTER INSERT ON methods BEGIN
            INSERT INTO methods_fts(rowid, slug, title, problem, method_text, code, tags, language)
            VALUES (new.id, new.slug, new.title, new.problem, new.method_text, new.code, new.tags, new.language);
        END;
        CREATE TRIGGER IF NOT EXISTS methods_ad AFTER DELETE ON methods BEGIN
            INSERT INTO methods_fts(methods_fts, rowid, slug, title, problem, method_text, code, tags, language)
            VALUES ('delete', old.id, old.slug, old.title, old.problem, old.method_text, old.code, old.tags, old.language);
        END;
        CREATE TRIGGER IF NOT EXISTS methods_au AFTER UPDATE ON methods BEGIN
            INSERT INTO methods_fts(methods_fts, rowid, slug, title, problem, method_text, code, tags, language)
            VALUES ('delete', old.id, old.slug, old.title, old.problem, old.method_text, old.code, old.tags, old.language);
            INSERT INTO methods_fts(rowid, slug, title, problem, method_text, code, tags, language)
            VALUES (new.id, new.slug, new.title, new.problem, new.method_text, new.code, new.tags, new.language);
        END;
    """)
    db.commit()


def index_method(db: sqlite3.Connection, data: dict):
    """Insert or update a method in the index."""
    tags = data.get("tags", [])
    if isinstance(tags, list):
        tags = ", ".join(tags)
    db.execute("""
        INSERT INTO methods (slug, file_path, title, problem, method_text, code, language, tags, source_project, created, updated, retrievals)
        VALUES (:slug, :file_path, :title, :problem, :method_text, :code, :language, :tags, :source_project, :created, :updated, :retrievals)
        ON CONFLICT(slug) DO UPDATE SET
            file_path=excluded.file_path, title=excluded.title, problem=excluded.problem,
            method_text=excluded.method_text, code=excluded.code, language=excluded.language,
            tags=excluded.tags, source_project=excluded.source_project,
            updated=excluded.updated, retrievals=excluded.retrievals
    """, {
        "slug": data.get("slug", ""),
        "file_path": data.get("file_path", ""),
        "title": data.get("title", ""),
        "problem": data.get("problem", ""),
        "method_text": data.get("method_text", ""),
        "code": data.get("code", ""),
        "language": data.get("language", ""),
        "tags": tags,
        "source_project": data.get("source_project", ""),
        "created": data.get("created", ""),
        "updated": data.get("updated", ""),
        "retrievals": data.get("retrievals", 0),
    })
    db.commit()


def reindex_all(db: sqlite3.Connection):
    """Rebuild the entire index from method files."""
    db.execute("DELETE FROM methods")
    db.execute("DELETE FROM methods_fts")
    db.commit()
    if not METHODS_DIR.exists():
        return
    for path in sorted(METHODS_DIR.glob("*.md")):
        data = read_method_file(path)
        if data:
            index_method(db, data)


def increment_retrieval(db: sqlite3.Connection, slug: str):
    """Increment the retrieval count for a method in the index and its file."""
    db.execute("UPDATE methods SET retrievals = retrievals + 1 WHERE slug = ?", (slug,))
    db.commit()
    # Also update the file
    row = db.execute("SELECT file_path, retrievals FROM methods WHERE slug = ?", (slug,)).fetchone()
    if row:
        path = Path(row["file_path"])
        if path.exists():
            text = path.read_text(encoding="utf-8")
            # Update retrievals in frontmatter
            text = re.sub(
                r"^retrievals:\s*\d+",
                f"retrievals: {row['retrievals']}",
                text,
                count=1,
                flags=re.MULTILINE,
            )
            path.write_text(text, encoding="utf-8")


# ---------------------------------------------------------------------------
# Next method number
# ---------------------------------------------------------------------------

def next_method_number() -> int:
    """Determine the next numeric prefix for a method file."""
    if not METHODS_DIR.exists():
        return 0
    existing = []
    for path in METHODS_DIR.glob("*.md"):
        match = re.match(r"^(\d+)-", path.name)
        if match:
            existing.append(int(match.group(1)))
    return max(existing, default=-1) + 1


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def cmd_init(_args):
    """Initialize the hoard directory and seed item 0."""
    METHODS_DIR.mkdir(parents=True, exist_ok=True)

    # Seed item 0 if not present
    heuristic_dest = METHODS_DIR / "000-discover-heuristic.md"
    heuristic_src = SEED_DIR / "000-discover-heuristic.md"
    if not heuristic_dest.exists() and heuristic_src.exists():
        shutil.copy2(heuristic_src, heuristic_dest)
        print(json.dumps({"action": "seeded", "file": str(heuristic_dest)}))
    elif heuristic_dest.exists():
        print(json.dumps({"action": "already_initialized", "hoard_dir": str(HOARD_DIR)}))
    else:
        print(json.dumps({"action": "initialized", "warning": "seed file not found", "hoard_dir": str(HOARD_DIR)}))

    # Build/rebuild index
    db = get_db()
    ensure_schema(db)
    reindex_all(db)
    db.close()


def cmd_stock(_args):
    """Stock a new method. Reads JSON from stdin."""
    data = json.loads(sys.stdin.read())

    num = next_method_number()
    slug = data.get("slug", f"method-{num}")
    filename = f"{num:03d}-{slug}.md"
    filepath = METHODS_DIR / filename

    today = str(date.today())
    tags = data.get("tags", [])
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.split(",") if t.strip()]

    meta = {
        "id": num,
        "slug": slug,
        "title": data.get("title", ""),
        "problem": data.get("problem", ""),
        "language": data.get("language", ""),
        "tags": tags,
        "source_project": data.get("source_project", ""),
        "created": today,
        "updated": today,
        "retrievals": 0,
    }

    body_parts = []
    if data.get("method_text"):
        body_parts.append(f"## Method\n\n{data['method_text']}")
    if data.get("code"):
        lang = data.get("language", "")
        body_parts.append(f"## Code\n\n```{lang}\n{data['code']}\n```")
    if data.get("context"):
        body_parts.append(f"## Context\n\n{data['context']}")

    content = render_frontmatter(meta) + "\n\n" + "\n\n".join(body_parts) + "\n"
    filepath.write_text(content, encoding="utf-8")

    # Update index
    db = get_db()
    ensure_schema(db)
    method_data = read_method_file(filepath)
    if method_data:
        index_method(db, method_data)
    db.close()

    print(json.dumps({"action": "stocked", "file": str(filepath), "slug": slug, "id": num}))


def cmd_search(args):
    """Search the hoard via FTS5."""
    query = " ".join(args.query)
    if not query:
        print(json.dumps({"error": "no query provided"}))
        sys.exit(1)

    db = get_db()
    ensure_schema(db)

    rows = db.execute("""
        SELECT m.*, snippet(methods_fts, 2, '>>>', '<<<', '...', 32) as snippet
        FROM methods_fts fts
        JOIN methods m ON m.id = fts.rowid
        WHERE methods_fts MATCH ?
        ORDER BY rank
        LIMIT 20
    """, (query,)).fetchall()

    results = []
    for row in rows:
        results.append({
            "id": row["id"],
            "slug": row["slug"],
            "title": row["title"],
            "problem": row["problem"],
            "language": row["language"],
            "tags": row["tags"],
            "snippet": row["snippet"],
            "retrievals": row["retrievals"],
            "file_path": row["file_path"],
        })
        increment_retrieval(db, row["slug"])

    db.close()
    print(json.dumps({"query": query, "count": len(results), "results": results}, indent=2))


def cmd_get(args):
    """Get a specific method by id or slug."""
    identifier = args.identifier

    db = get_db()
    ensure_schema(db)

    # Try as numeric id first
    row = None
    if identifier.isdigit():
        row = db.execute("SELECT * FROM methods WHERE id = ?", (int(identifier),)).fetchone()

    # Try as slug
    if row is None:
        row = db.execute("SELECT * FROM methods WHERE slug = ?", (identifier,)).fetchone()

    # Try as filename prefix (e.g., "000-discover-heuristic")
    if row is None:
        row = db.execute("SELECT * FROM methods WHERE slug = ?",
                         (re.sub(r"^\d+-", "", identifier),)).fetchone()

    if row is None:
        print(json.dumps({"error": f"method not found: {identifier}"}))
        sys.exit(1)

    increment_retrieval(db, row["slug"])

    # Read the full file content
    path = Path(row["file_path"])
    content = path.read_text(encoding="utf-8") if path.exists() else ""

    result = dict(row)
    result["content"] = content
    db.close()

    print(json.dumps(result, indent=2))


def cmd_heuristic(_args):
    """Output item 0 — the discover heuristic."""
    path = METHODS_DIR / "000-discover-heuristic.md"
    if not path.exists():
        print(json.dumps({"error": "heuristic not found — run 'init' first"}))
        sys.exit(1)

    content = path.read_text(encoding="utf-8")
    print(json.dumps({"file": str(path), "content": content}))


def cmd_list(_args):
    """List all methods in the hoard."""
    db = get_db()
    ensure_schema(db)

    rows = db.execute("""
        SELECT id, slug, title, tags, language, retrievals, created, updated
        FROM methods ORDER BY id
    """).fetchall()

    methods = [dict(r) for r in rows]
    db.close()

    print(json.dumps({"count": len(methods), "methods": methods}, indent=2))


def cmd_update(_args):
    """Update an existing method. Reads JSON from stdin with 'slug' field to identify."""
    data = json.loads(sys.stdin.read())
    slug = data.get("slug")
    if not slug:
        print(json.dumps({"error": "JSON must include 'slug' field"}))
        sys.exit(1)

    db = get_db()
    ensure_schema(db)
    row = db.execute("SELECT file_path FROM methods WHERE slug = ?", (slug,)).fetchone()
    if not row:
        print(json.dumps({"error": f"method not found: {slug}"}))
        sys.exit(1)

    path = Path(row["file_path"])
    existing = read_method_file(path)
    if not existing:
        print(json.dumps({"error": f"could not read file: {path}"}))
        sys.exit(1)

    # Merge: incoming data overrides existing
    meta, _ = parse_frontmatter(path.read_text(encoding="utf-8"))
    for k, v in data.items():
        if k not in ("method_text", "code", "context", "raw_body", "file_path", "file_name"):
            meta[k] = v
    meta["updated"] = str(date.today())

    body_parts = []
    method_text = data.get("method_text", existing.get("method_text", ""))
    code = data.get("code", existing.get("code", ""))
    context = data.get("context", existing.get("context", ""))
    lang = meta.get("language", "")

    if method_text:
        body_parts.append(f"## Method\n\n{method_text}")
    if code:
        body_parts.append(f"## Code\n\n```{lang}\n{code}\n```")
    if context:
        body_parts.append(f"## Context\n\n{context}")

    content = render_frontmatter(meta) + "\n\n" + "\n\n".join(body_parts) + "\n"
    path.write_text(content, encoding="utf-8")

    # Re-index
    method_data = read_method_file(path)
    if method_data:
        index_method(db, method_data)
    db.close()

    print(json.dumps({"action": "updated", "slug": slug, "file": str(path)}))


def cmd_reindex(_args):
    """Rebuild the FTS5 index from method files."""
    db = get_db()
    ensure_schema(db)
    reindex_all(db)
    count = db.execute("SELECT COUNT(*) FROM methods").fetchone()[0]
    db.close()
    print(json.dumps({"action": "reindexed", "count": count}))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="method-hoard CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("init", help="Initialize hoard and seed item 0")
    sub.add_parser("stock", help="Stock a new method (reads JSON from stdin)")

    p_search = sub.add_parser("search", help="Search the hoard")
    p_search.add_argument("query", nargs="+", help="Search query")

    p_get = sub.add_parser("get", help="Get a method by id or slug")
    p_get.add_argument("identifier", help="Method id or slug")

    sub.add_parser("heuristic", help="Output the discover heuristic (item 0)")
    sub.add_parser("list", help="List all methods")
    sub.add_parser("update", help="Update a method (reads JSON from stdin)")
    sub.add_parser("reindex", help="Rebuild the FTS5 index")

    args = parser.parse_args()

    dispatch = {
        "init": cmd_init,
        "stock": cmd_stock,
        "search": cmd_search,
        "get": cmd_get,
        "heuristic": cmd_heuristic,
        "list": cmd_list,
        "update": cmd_update,
        "reindex": cmd_reindex,
    }

    dispatch[args.command](args)


if __name__ == "__main__":
    main()
