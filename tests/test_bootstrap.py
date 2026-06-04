import tempfile
import unittest
from pathlib import Path

from stock_agent_orchestrator.persistence.sqlite_store import SQLiteTaskStore
from stock_agent_orchestrator.services.demo import write_demo_sample
from stock_agent_orchestrator.services.doctor import run_doctor
from stock_agent_orchestrator.services.shadow_replay import ShadowReplayService


class BootstrapTests(unittest.TestCase):
    def test_doctor_creates_runtime_dir(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runtime_dir = Path(tmp) / "runtime"

            report = run_doctor(runtime_dir)

            self.assertTrue(report.ok)
            self.assertTrue(runtime_dir.exists())

    def test_demo_sample_replays(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runtime_dir = Path(tmp)
            sample = write_demo_sample(runtime_dir / "demo.jsonl")
            store = SQLiteTaskStore(runtime_dir / "demo.db")

            report = ShadowReplayService().replay_file(sample, store)

            self.assertEqual(report.imported_messages, 4)
            self.assertEqual(report.created_tasks, 1)
            self.assertGreaterEqual(report.advanced_events, 2)


if __name__ == "__main__":
    unittest.main()
