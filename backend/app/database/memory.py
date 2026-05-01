"""
memory.py
---------
File-backed storage layer that replaces MongoDB.
Data is persisted to JSON files on disk so it survives server restarts.
No external database required.
"""

import json
import logging
import os
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Storage directory — sits next to the backend folder
_STORAGE_DIR = Path(__file__).resolve().parent.parent.parent / ".data"


class FileBackedCollection:
    """Drop-in async replacement for a Motor collection, backed by a JSON file."""

    def __init__(self, name: str = "unnamed"):
        self.name = name
        self._file = _STORAGE_DIR / f"{name}.json"
        self.data: dict[str, dict] = {}
        self._load()

    # ── Persistence helpers ───────────────────────────────────────────────

    def _load(self):
        """Load data from disk if it exists."""
        if self._file.exists():
            try:
                with open(self._file, "r", encoding="utf-8") as f:
                    self.data = json.load(f)
                logger.info(
                    "Loaded %d docs from '%s'", len(self.data), self._file.name
                )
            except (json.JSONDecodeError, Exception) as exc:
                logger.warning("Could not load %s: %s — starting fresh", self._file, exc)
                self.data = {}
        else:
            self.data = {}

    def _save(self):
        """Persist data to disk."""
        _STORAGE_DIR.mkdir(parents=True, exist_ok=True)
        try:
            with open(self._file, "w", encoding="utf-8") as f:
                json.dump(self.data, f, ensure_ascii=False, default=str)
        except Exception as exc:
            logger.error("Failed to save %s: %s", self._file, exc)

    # ── Collection API (async, matching Motor interface) ──────────────────

    async def insert_one(self, doc: dict):
        _id = os.urandom(12).hex()
        doc["_id"] = _id
        self.data[_id] = doc
        self._save()

        class InsertResult:
            inserted_id = _id

        logger.debug("Inserted doc into '%s': id=%s", self.name, _id)
        return InsertResult()

    async def find_one(self, query: dict) -> Optional[dict]:
        # Direct _id lookup
        if "_id" in query:
            return self.data.get(str(query["_id"]))
        # Search by any field
        for doc in self.data.values():
            if all(doc.get(k) == v for k, v in query.items()):
                return doc
        return None

    async def update_one(self, query: dict, update: dict, upsert: bool = False):
        doc = await self.find_one(query)
        if doc is None and upsert:
            new_doc = update.get("$set", {})
            new_doc.update(query)
            _id = os.urandom(12).hex()
            new_doc["_id"] = _id
            self.data[_id] = new_doc
            self._save()
            return
        if doc:
            set_data = update.get("$set", {})
            doc.update(set_data)
            self._save()

    async def replace_one(self, query: dict, replacement: dict, upsert: bool = False):
        doc = await self.find_one(query)
        if doc is not None:
            _id = doc["_id"]
            replacement["_id"] = _id
            self.data[_id] = replacement
            self._save()
        elif upsert:
            _id = os.urandom(12).hex()
            replacement["_id"] = _id
            self.data[_id] = replacement
            self._save()

    async def find(self, query: dict = None):
        """Return all matching docs (simple list)."""
        query = query or {}
        results = []
        for doc in self.data.values():
            if all(doc.get(k) == v for k, v in query.items()):
                results.append(doc)
        return results


# ── Singleton collections ─────────────────────────────────────────────────────
_resumes = FileBackedCollection("resumes")
_recommendations = FileBackedCollection("recommendations")


async def connect_db() -> None:
    logger.info("✅ Using file-backed storage at: %s", _STORAGE_DIR.resolve())


async def close_db() -> None:
    logger.info("File-backed storage synced. Data persisted to disk.")


def get_db():
    return True


def get_resumes_collection():
    return _resumes


def get_recommendations_collection():
    return _recommendations


async def ping_db() -> bool:
    return True