import tempfile
import unittest
from pathlib import Path

from stock_agent_orchestrator.bridges.current_stack import CurrentStackBridge


class CurrentStackBridgeTests(unittest.TestCase):
    def test_read_candidate_pool_parses_main_table(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            candidate_file = Path(tmp) / "candidate_list.md"
            candidate_file.write_text(
                """# demo

## 🎯 候选股（已收敛，2只）
| 标的 | 代码 | 现价 | RSI | 今日涨跌 | 原因 |
|------|------|------|-----|---------|------|
| 山西汾酒 | 600809 | 123.5 | 30.75 | -1.75% | 白酒超跌 |
| 华域汽车 | 600741 | 17.07 | 30.79 | +0.59% | 汽车零部件 |

## ❌ 已排除（问题股）
| 标的 | 代码 | 排除原因 |
|------|------|---------|
| *ST国中 | 600187 | *ST退市风险 |
""",
                encoding="utf-8",
            )

            bridge = CurrentStackBridge(candidate_file=candidate_file)
            snapshot = bridge.read_candidate_pool()

            self.assertEqual(len(snapshot.candidates), 2)
            self.assertEqual(snapshot.candidates[0].code, "600809")
            self.assertEqual(snapshot.candidates[1].reason, "汽车零部件")


if __name__ == "__main__":
    unittest.main()
