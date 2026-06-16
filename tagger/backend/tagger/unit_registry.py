from __future__ import annotations

from collections import OrderedDict


class UnitRegistry:
    def __init__(self):
        self._units: OrderedDict[str, dict] = OrderedDict()

    def register(self, unit_id: str, measure: str) -> str:
        if unit_id not in self._units:
            self._units[unit_id] = {"id": unit_id, "measure": measure}
        return unit_id

    def values(self) -> list[dict]:
        return list(self._units.values())

