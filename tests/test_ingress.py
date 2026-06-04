import unittest

from stock_agent_orchestrator.connectors.feishu import FeishuMessageEvent
from stock_agent_orchestrator.services.ingress import BoundedIngressQueue, IngressItem, IngressQueueFullError


def event(message_id: str) -> FeishuMessageEvent:
    return FeishuMessageEvent(
        event_id=f"evt-{message_id}",
        chat_id="chat",
        sender_open_id="user",
        sender_name="BOOS",
        text="@小C-beta 今天先给我一份候选池",
        mentions=("owner",),
        message_id=message_id,
    )


class IngressQueueTests(unittest.TestCase):
    def test_dequeue_is_fair_across_instances(self) -> None:
        queue = BoundedIngressQueue(max_per_instance=10)
        queue.enqueue(IngressItem("a", event("a1")))
        queue.enqueue(IngressItem("a", event("a2")))
        queue.enqueue(IngressItem("b", event("b1")))

        self.assertEqual(queue.dequeue().event.message_id, "a1")
        self.assertEqual(queue.dequeue().event.message_id, "b1")
        self.assertEqual(queue.dequeue().event.message_id, "a2")
        self.assertIsNone(queue.dequeue())

    def test_overload_is_counted(self) -> None:
        queue = BoundedIngressQueue(max_per_instance=1)
        queue.enqueue(IngressItem("beta", event("m1")))

        with self.assertRaises(IngressQueueFullError):
            queue.enqueue(IngressItem("beta", event("m2")))

        stats = queue.stats("beta")
        self.assertEqual(stats.current_depth, 1)
        self.assertEqual(stats.peak_depth, 1)
        self.assertEqual(stats.overload_count, 1)


if __name__ == "__main__":
    unittest.main()
