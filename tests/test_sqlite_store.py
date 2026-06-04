import tempfile
import unittest
from pathlib import Path

from stock_agent_orchestrator.domain.models import TaskIntent
from stock_agent_orchestrator.persistence.sqlite_store import SQLiteTaskStore
from stock_agent_orchestrator.services.task_engine import TaskEngine


class SQLiteStoreTests(unittest.TestCase):
    def test_sqlite_store_saves_task(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "tasks.db"
            store = SQLiteTaskStore(db_path)
            store.init_db()

            task = TaskEngine().create_task(
                task_id="TASK-2001",
                title="store test",
                intent=TaskIntent.DAILY_CANDIDATE_POOL,
            )
            store.save_task(task)

            row = store.get_task_row("TASK-2001")
            self.assertIsNotNone(row)
            self.assertEqual(row["title"], "store test")

            loaded = store.load_task("TASK-2001")
            self.assertIsNotNone(loaded)
            assert loaded is not None
            self.assertEqual(loaded.task_id, "TASK-2001")
            self.assertEqual(len(loaded.events), 2)


if __name__ == "__main__":
    unittest.main()
