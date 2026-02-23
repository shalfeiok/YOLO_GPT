"""Docs service: scan docs tree, read files, and cache content."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class DocEntry:
    relative_path: str
    absolute_path: Path


class DocsService:
    SUPPORTED_SUFFIXES = {".md", ".txt", ".rst"}

    def __init__(self, docs_root: Path) -> None:
        self._docs_root = docs_root
        self._cache: dict[Path, str] = {}

    @property
    def docs_root(self) -> Path:
        return self._docs_root

    def ensure_docs_root(self) -> None:
        self._docs_root.mkdir(parents=True, exist_ok=True)
        index = self._docs_root / "README.md"
        if not index.exists():
            index.write_text(
                "# Документация\n\n"
                "Папка `docs/` содержит пользовательскую и техническую документацию проекта.\n",
                encoding="utf-8",
            )

    def list_docs(self) -> list[DocEntry]:
        self.ensure_docs_root()
        entries: list[DocEntry] = []
        for path in sorted(self._docs_root.rglob("*")):
            if not path.is_file() or path.suffix.lower() not in self.SUPPORTED_SUFFIXES:
                continue
            entries.append(
                DocEntry(
                    relative_path=path.relative_to(self._docs_root).as_posix(),
                    absolute_path=path,
                )
            )
        return entries

    def read_doc(self, relative_path: str) -> str:
        path = (self._docs_root / relative_path).resolve()
        if path in self._cache:
            return self._cache[path]
        text = path.read_text(encoding="utf-8")
        self._cache[path] = text
        return text

    def find_by_name(self, query: str) -> list[DocEntry]:
        q = query.strip().lower()
        docs = self.list_docs()
        if not q:
            return docs
        return [entry for entry in docs if q in entry.relative_path.lower()]

    def search_content(self, query: str) -> list[DocEntry]:
        q = query.strip().lower()
        if not q:
            return []
        results: list[DocEntry] = []
        for entry in self.list_docs():
            try:
                text = self.read_doc(entry.relative_path)
            except OSError:
                continue
            if q in text.lower():
                results.append(entry)
        return results
