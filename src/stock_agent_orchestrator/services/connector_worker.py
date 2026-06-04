from __future__ import annotations

from dataclasses import dataclass

from stock_agent_orchestrator.services.beta_orchestrator import BetaOrchestratorService, BetaProcessResult
from stock_agent_orchestrator.services.ingress import BoundedIngressQueue, IngressItem, IngressStats


@dataclass(frozen=True, slots=True)
class WorkerRunReport:
    processed: int
    handled: int
    ignored: int
    results: list[BetaProcessResult]


class ConnectorWorker:
    """Drains gateway ingress and delegates business handling to the orchestrator."""

    def __init__(self, *, queue: BoundedIngressQueue, orchestrator: BetaOrchestratorService) -> None:
        self.queue = queue
        self.orchestrator = orchestrator

    def enqueue(self, item: IngressItem) -> None:
        self.queue.enqueue(item)

    def drain_once(self, *, limit: int = 100) -> WorkerRunReport:
        processed = 0
        handled = 0
        ignored = 0
        results: list[BetaProcessResult] = []

        while processed < limit:
            item = self.queue.dequeue()
            if item is None:
                break
            result = self.orchestrator.process_message(item.event)
            results.append(result)
            processed += 1
            if result.handled:
                handled += 1
            else:
                ignored += 1

        return WorkerRunReport(processed=processed, handled=handled, ignored=ignored, results=results)

    def stats(self, instance_id: str) -> IngressStats:
        return self.queue.stats(instance_id)
