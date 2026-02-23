from __future__ import annotations

from app.application.docs_service import DocEntry, DocsService


class DocsViewModel:
    def __init__(self, docs_service: DocsService) -> None:
        self._docs_service = docs_service

    @property
    def docs_root(self):
        return self._docs_service.docs_root

    def list_docs(self) -> list[DocEntry]:
        return self._docs_service.list_docs()

    def filter_by_name(self, query: str) -> list[DocEntry]:
        return self._docs_service.find_by_name(query)

    def search_content(self, query: str) -> list[DocEntry]:
        return self._docs_service.search_content(query)

    def read_doc(self, relative_path: str) -> str:
        return self._docs_service.read_doc(relative_path)
