from __future__ import annotations

import argparse
import json
from pathlib import Path

from _bootstrap import SKILL_ROOT  # noqa: F401
from runtime.client import AgentGatewayError, AgentGatewayTransportError, GatewayClient
from runtime.config import ClawborateConfig
from runtime.skill_runtime import InstallError, install_skill


def emit_error(code: str, message: str) -> None:
    print(json.dumps({"error": code, "message": message}, indent=2, ensure_ascii=False))


def main() -> None:
    parser = argparse.ArgumentParser(description="Install the Clawborate OpenClaw skill runtime")
    parser.add_argument("--agent-key", help="Long-lived Clawborate agent key")
    parser.add_argument("--skill-home", help="Override skill storage directory")
    parser.add_argument("--agent-contact", help="Optional agent contact to attach on auto-submit")
    parser.add_argument("--openclaw-root", help="Local OpenClaw root, defaults to ~/.openclaw")
    parser.add_argument("--openclaw-cli", help="OpenClaw CLI executable or full command prefix")
    parser.add_argument("--patrol-agent", help="OpenClaw agent id for patrol cron")
    parser.add_argument("--patrol-session", help="OpenClaw session name for patrol cron")
    parser.add_argument("--patrol-every-minutes", type=int, help="Cron cadence in minutes")
    args = parser.parse_args()

    agent_key = (args.agent_key or "").strip()
    if not agent_key:
        agent_key = input("Enter Clawborate Agent Key: ").strip()
    if not agent_key:
        raise SystemExit("Agent key is required.")
    if not agent_key.startswith("cm_sk_live_"):
        emit_error("invalid_agent_key_format", "Clawborate agent keys must start with cm_sk_live_.")
        raise SystemExit(1)

    home = Path(args.skill_home).expanduser() if args.skill_home else None
    config = ClawborateConfig(
        agent_contact=args.agent_contact,
        openclaw_root=args.openclaw_root or ClawborateConfig().openclaw_root,
        openclaw_cli=args.openclaw_cli,
        patrol_agent=args.patrol_agent or ClawborateConfig().patrol_agent,
        patrol_session=args.patrol_session or ClawborateConfig().patrol_session,
        patrol_every_minutes=args.patrol_every_minutes or ClawborateConfig().patrol_every_minutes,
    )
    client = GatewayClient(agent_key=agent_key, base_url=config.base_url, anon_key=config.anon_key)
    try:
        client.probe_rpc_connectivity()
    except AgentGatewayTransportError as exc:
        emit_error("network_error", str(exc))
        raise SystemExit(1) from exc
    except AgentGatewayError as exc:
        emit_error(exc.code, exc.message)
        raise SystemExit(1) from exc

    try:
        result = install_skill(agent_key=agent_key, home=home, config=config)
    except InstallError as exc:
        code = "permission_denied" if exc.code == "missing_scope" else exc.code
        emit_error(code, exc.message)
        raise SystemExit(1) from exc

    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
