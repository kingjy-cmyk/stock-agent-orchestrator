from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Deque

from stock_agent_orchestrator.connectors.feishu import FeishuMessageEvent


class IngressQueueFullError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class IngressItem:
    instance_id: str
    event: FeishuMessageEvent


@dataclass(frozen=True, slots=True)
class IngressStats:
    current_depth: int
    peak_depth: int
    overload_count: int


class BoundedIngressQueue:
    """Small fair queue between Feishu gateway input and orchestrator work.

    This mirrors the important part of the Codex Feishu two-process connector:
    platform ingress should enqueue quickly, while business logic drains work
    separately. This prevents callback handlers from blocking or being
    redelivered by the platform.
    """

    def __init__(self, *, max_per_instance: int = 1024) -> None:
        self.max_per_instance = max_per_instance
        self._queues: dict[str, Deque[IngressItem]] = {}
        self._ready: Deque[str] = deque()
        self._ready_set: set[str] = set()
        self._peak_depth: dict[str, int] = {}
        self._overload_count: dict[str, int] = {}

    def enqueue(self, item: IngressItem) -> None:
        instance_id = item.instance_id.strip()
        if not instance_id:
            raise ValueError("ingress item requires instance_id")
        queue = self._queues.setdefault(instance_id, deque())
        if self.max_per_instance > 0 and len(queue) >= self.max_per_instance:
            self._overload_count[instance_id] = self._overload_count.get(instance_id, 0) + 1
            raise IngressQueueFullError(f"ingress queue full: {instance_id}")
        queue.append(item)
        self._peak_depth[instance_id] = max(self._peak_depth.get(instance_id, 0), len(queue))
        if instance_id not in self._ready_set:
            self._ready.append(instance_id)
            self._ready_set.add(instance_id)

    def dequeue(self) -> IngressItem | None:
        if not self._ready:
            return None
        instance_id = self._ready.popleft()
        queue = self._queues[instance_id]
        item = queue.popleft()
        if queue:
            self._ready.append(instance_id)
        else:
            del self._queues[instance_id]
            self._ready_set.remove(instance_id)
        return item

    def stats(self, instance_id: str) -> IngressStats:
        key = instance_id.strip()
        return IngressStats(
            current_depth=len(self._queues.get(key, ())),
            peak_depth=self._peak_depth.get(key, 0),
            overload_count=self._overload_count.get(key, 0),
        )
