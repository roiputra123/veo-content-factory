import json
import os
import uuid
from datetime import datetime

_LIBRARY_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "storage", "prompts")
_LIBRARY_PATH = os.path.join(_LIBRARY_DIR, "library.json")


class PromptLibrary:
    def __init__(self):
        self._ensure_storage()

    def _ensure_storage(self):
        os.makedirs(_LIBRARY_DIR, exist_ok=True)
        if not os.path.exists(_LIBRARY_PATH):
            with open(_LIBRARY_PATH, "w") as f:
                json.dump([], f)

    def _load_all(self):
        with open(_LIBRARY_PATH, "r") as f:
            return json.load(f)

    def _save_all(self, data):
        with open(_LIBRARY_PATH, "w") as f:
            json.dump(data, f, indent=2)

    def save(self, prompt_data):
        entries = self._load_all()
        entry = {
            "id": str(uuid.uuid4()),
            "niche": prompt_data.get("niche", ""),
            "user_input": prompt_data.get("user_input", ""),
            "positive": prompt_data.get("positive", ""),
            "negative": prompt_data.get("negative", ""),
            "score": prompt_data.get("score", 0),
            "feedback": prompt_data.get("feedback", ""),
            "iterations": prompt_data.get("iterations", []),
            "parent_id": prompt_data.get("parent_id"),
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }
        entries.append(entry)
        self._save_all(entries)
        return entry["id"]

    def update(self, entry_id, prompt_data):
        entries = self._load_all()
        for e in entries:
            if e["id"] == entry_id:
                e.update({k: v for k, v in prompt_data.items() if v is not None})
                e["updated_at"] = datetime.now().isoformat()
                self._save_all(entries)
                return True
        return False

    def get(self, entry_id):
        for e in self._load_all():
            if e["id"] == entry_id:
                return e
        return None

    def list(self, niche=None, sort_by="created_at", limit=50):
        entries = self._load_all()
        if niche:
            entries = [e for e in entries if e.get("niche") == niche]
        entries.sort(key=lambda e: e.get(sort_by, ""), reverse=True)
        return entries[:limit]

    def search(self, query):
        q = query.lower()
        return [e for e in self._load_all() if q in e.get("user_input", "").lower()
                or q in e.get("positive", "").lower()
                or q in e.get("feedback", "").lower()]

    def delete(self, entry_id):
        entries = self._load_all()
        entries = [e for e in entries if e["id"] != entry_id]
        self._save_all(entries)
        return True

    def get_chain(self, entry_id):
        entries = self._load_all()
        chain = []
        current = entry_id
        while current:
            entry = next((e for e in entries if e["id"] == current), None)
            if entry:
                chain.append(entry)
                current = entry.get("parent_id")
            else:
                break
        return chain

    def get_children(self, entry_id):
        return [e for e in self._load_all() if e.get("parent_id") == entry_id]
