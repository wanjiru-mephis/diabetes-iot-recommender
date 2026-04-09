"""Initialize the database schema. Run from the backend/ directory:

    python ../scripts/init_db.py
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "backend")))

from app.database import init_db  # noqa: E402

if __name__ == "__main__":
    init_db()
    print("Database initialized.")
