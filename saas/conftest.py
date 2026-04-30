import os
import sys

# Must be set before any app module is imported to satisfy database.py.
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test")

# Make the saas/ directory importable as root so "from app.xxx" works.
sys.path.insert(0, os.path.dirname(__file__))
