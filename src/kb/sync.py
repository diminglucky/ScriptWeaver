from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class SyncStats:
    scanned: int = 0
    indexed: int = 0
    updated: int = 0
    skipped: int = 0
    removed: int = 0
    chunk_count: int = 0
    errors: list[str] = field(default_factory=list)

    def summary(self) -> str:
        parts = [
            f"扫描 {self.scanned}",
            f"新增 {self.indexed}",
            f"更新 {self.updated}",
            f"跳过 {self.skipped}",
            f"删除 {self.removed}",
            f"chunk {self.chunk_count}",
        ]
        return "，".join(parts)
