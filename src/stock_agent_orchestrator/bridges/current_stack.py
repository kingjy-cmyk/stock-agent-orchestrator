from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from stock_agent_orchestrator.schemas.research import Candidate, CandidatePoolSnapshot, SevenLayerCard


DEFAULT_CANDIDATE_FILE = Path("/home/jy95/.openclaw/evolution/shared/recurring/candidate_list.md")


@dataclass(slots=True)
class CurrentStackBridge:
    candidate_file: Path = DEFAULT_CANDIDATE_FILE

    def read_candidate_pool(self, path: Path | None = None) -> CandidatePoolSnapshot:
        target = path or self.candidate_file
        content = target.read_text(encoding="utf-8", errors="ignore")
        candidates: list[Candidate] = []
        in_table = False

        for raw_line in content.splitlines():
            line = raw_line.strip()
            if line.startswith("##"):
                if "候选股" in line and "排除" not in line:
                    in_table = True
                    continue
                if in_table:
                    break
            if not in_table or not line.startswith("|"):
                continue
            if "标的" in line or "------" in line or "（无）" in line:
                continue
            parts = [part.strip() for part in line.split("|")[1:-1]]
            if len(parts) < 6:
                continue
            name, code, price, rsi, day_change, reason = parts[:6]
            if not re.fullmatch(r"\d{6}", code):
                continue
            candidates.append(
                Candidate(
                    name=name,
                    code=code,
                    price=self._safe_float(price),
                    rsi=self._safe_float(rsi),
                    day_change=day_change,
                    reason=reason,
                )
            )

        return CandidatePoolSnapshot(
            source_path=str(target),
            as_of=target.stat().st_mtime_ns.__str__(),
            candidates=candidates,
        )

    def parse_seven_layer_report(self, path: Path) -> list[SevenLayerCard]:
        content = path.read_text(encoding="utf-8", errors="ignore").splitlines()
        cards: list[SevenLayerCard] = []
        current: dict[str, str] = {}

        def flush() -> None:
            if not current:
                return
            cards.append(
                SevenLayerCard(
                    name=current["name"],
                    code=current["code"],
                    layer_1_market=current.get("L1", ""),
                    layer_2_rsi=current.get("L2", ""),
                    layer_3_financials=current.get("L3", ""),
                    layer_4_fund_flow=current.get("L4", ""),
                    layer_5_catalysts=current.get("L5", ""),
                    layer_6_theme=current.get("L6", ""),
                    layer_7_risks=current.get("L7", ""),
                )
            )

        for line in content:
            stripped = line.strip()
            if stripped.startswith("■ "):
                if current:
                    flush()
                    current = {}
                match = re.match(r"■\s+(.+)\((\d{6})\)", stripped)
                if match:
                    current["name"] = match.group(1)
                    current["code"] = match.group(2)
                continue
            if not current:
                continue
            for key in ("L1", "L2", "L3", "L4", "L5", "L6", "L7"):
                prefix = f"{key} "
                if stripped.startswith(prefix):
                    current[key] = stripped
                    break

        if current:
            flush()
        return cards

    @staticmethod
    def _safe_float(text: str) -> float:
        clean = text.replace("%", "").replace(",", "").strip()
        try:
            return float(clean)
        except ValueError:
            return 0.0

