from __future__ import annotations

# Deprecated one-time migration utility retained for history/reference only.
# Prefer explicit Alembic migrations for new schema/data migrations.

import argparse
import json
import sys
from pathlib import Path


# Allow `python scripts/rename_context_bundle_keys.py` from backend/ to resolve `src.*`.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.db.models.project import Project  # noqa: E402
from src.db.session import SessionLocal, init_engine  # noqa: E402


AUDIENCE_FAMILIARITY_MAP = {
    "beginner": "new",
    "intermediate": "somewhat_familiar",
    "expert": "very_familiar",
}

DETAIL_LEVEL_MAP = {
    "surface": "quick_take",
    "intermediate": "practical",
    "deep": "deep_dive",
}


def _normalize_context(bundle: dict) -> tuple[dict, bool]:
    changed = False
    out = dict(bundle)

    old_domain = out.get("domain_level")
    old_depth = out.get("content_depth")
    has_new_audience = "audience_familiarity" in out and out.get("audience_familiarity") is not None
    has_new_detail = "detail_level" in out and out.get("detail_level") is not None

    if not has_new_audience and isinstance(old_domain, str) and old_domain.strip():
        out["audience_familiarity"] = AUDIENCE_FAMILIARITY_MAP.get(old_domain.strip(), old_domain.strip())
        changed = True

    if not has_new_detail and isinstance(old_depth, str) and old_depth.strip():
        out["detail_level"] = DETAIL_LEVEL_MAP.get(old_depth.strip(), old_depth.strip())
        changed = True

    if "domain_level" in out:
        out.pop("domain_level", None)
        changed = True
    if "content_depth" in out:
        out.pop("content_depth", None)
        changed = True

    return out, changed


def main() -> int:
    parser = argparse.ArgumentParser(description="Rename legacy context bundle keys in projects.context_json.")
    parser.add_argument("--dry-run", action="store_true", help="Print counts only; do not commit updates.")
    args = parser.parse_args()

    init_engine()
    updated = 0
    scanned = 0

    with SessionLocal() as db:
        rows = db.query(Project).all()
        scanned = len(rows)
        for row in rows:
            raw = row.context_json or "{}"
            try:
                bundle = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if not isinstance(bundle, dict):
                continue
            normalized, changed = _normalize_context(bundle)
            if not changed:
                continue
            updated += 1
            if not args.dry_run:
                row.context_json = json.dumps(normalized, ensure_ascii=False)

        if not args.dry_run:
            db.commit()

    print(f"projects_scanned={scanned}")
    print(f"projects_updated={updated}")
    print(f"mode={'dry_run' if args.dry_run else 'apply'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
