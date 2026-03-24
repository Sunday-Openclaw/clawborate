from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

OFFICIAL_BASE_URL = "https://xjljjxogsxumcnjyetwy.supabase.co"
OFFICIAL_ANON_KEY = "sb_publishable_dlgv32Zav_IaU_l6LVYu0A_CIz-Ww_u"
DEFAULT_WORKER_TICK_SECONDS = 300
DEFAULT_OPENCLAW_ROOT = str(Path.home() / ".openclaw")
DEFAULT_PATROL_SESSION = "clawborate-patrol"
DEFAULT_PATROL_AGENT = "main"
DEFAULT_PATROL_INTERVAL_MINUTES = 5


@dataclass(frozen=True)
class ClawborateConfig:
    base_url: str = OFFICIAL_BASE_URL
    anon_key: str = OFFICIAL_ANON_KEY
    worker_tick_seconds: int = DEFAULT_WORKER_TICK_SECONDS
    agent_contact: str | None = None
    openclaw_root: str = DEFAULT_OPENCLAW_ROOT
    openclaw_cli: str | None = None
    patrol_agent: str = DEFAULT_PATROL_AGENT
    patrol_session: str = DEFAULT_PATROL_SESSION
    patrol_every_minutes: int = DEFAULT_PATROL_INTERVAL_MINUTES

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> ClawborateConfig:
        payload = data or {}
        return cls(
            base_url=str(payload.get("base_url") or OFFICIAL_BASE_URL),
            anon_key=str(payload.get("anon_key") or OFFICIAL_ANON_KEY),
            worker_tick_seconds=int(payload.get("worker_tick_seconds") or DEFAULT_WORKER_TICK_SECONDS),
            agent_contact=payload.get("agent_contact"),
            openclaw_root=str(payload.get("openclaw_root") or DEFAULT_OPENCLAW_ROOT),
            openclaw_cli=payload.get("openclaw_cli"),
            patrol_agent=str(payload.get("patrol_agent") or DEFAULT_PATROL_AGENT),
            patrol_session=str(payload.get("patrol_session") or DEFAULT_PATROL_SESSION),
            patrol_every_minutes=int(payload.get("patrol_every_minutes") or DEFAULT_PATROL_INTERVAL_MINUTES),
        )
