#!/usr/bin/env python
"""Upserts the Stage 6 exercise library (app/exercise_library.py) into the `exercises` table.

Idempotent — matched by `name`, safe to re-run any time the library changes. The library itself
is checked into the repo as plain Python (see app/exercise_library.py's docstring for why), so
this script only needs to be re-run when that file changes:

    apps/api/.venv/Scripts/python.exe apps/api/scripts/seed_exercises.py
"""

import sys

from app.database import SessionLocal
from app.exercise_library import SEED_EXERCISES
from app.models import Exercise


def main() -> None:
    db = SessionLocal()
    try:
        existing = {row.name: row for row in db.query(Exercise).all()}
        created, updated = 0, 0
        for defn in SEED_EXERCISES:
            row = existing.get(defn.name)
            if row is None:
                row = Exercise(name=defn.name)
                db.add(row)
                created += 1
            else:
                updated += 1
            row.category = defn.category
            row.purpose = defn.purpose
            row.instructions = defn.instructions
            row.duration_seconds = defn.duration_seconds
            row.difficulty = defn.difficulty
            row.contraindications = defn.contraindications
            row.target_measurement = defn.target_measurement
            row.expected_result = defn.expected_result
            row.is_active = True
        db.commit()
        print(f"seeded {len(SEED_EXERCISES)} exercises ({created} created, {updated} updated)")
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
