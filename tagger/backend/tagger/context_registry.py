from __future__ import annotations

from collections import OrderedDict
from typing import Any


class ContextRegistry:
    def __init__(self):
        self._contexts: OrderedDict[str, dict[str, Any]] = OrderedDict()

    def register(self, context_id: str, payload: dict[str, Any]) -> str:
        if context_id not in self._contexts:
            self._contexts[context_id] = payload
        return context_id

    def values(self) -> list[dict[str, Any]]:
        return list(self._contexts.values())

