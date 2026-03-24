import json
from datetime import datetime, timedelta, timezone

import skill_runtime.runner as policy_runner


def test_run_once_handles_zero_projects(tmp_path, monkeypatch):
    monkeypatch.setattr(policy_runner, "list_my_projects", lambda *args, **kwargs: [])
    monkeypatch.setattr(policy_runner, "list_incoming_interests", lambda *args, **kwargs: [])

    summary = policy_runner.run_once(
        agent_key="agent-key",
        state_file=tmp_path / "state.json",
        report_dir=tmp_path / "reports",
        now=datetime(2026, 3, 21, 12, 0, tzinfo=timezone.utc),
    )

    assert summary["project_count"] == 0
    assert summary["projects"] == []
    assert summary["incoming_interests"] == []
    assert (tmp_path / "reports" / "latest-summary.json").exists()


def test_run_once_builds_agent_first_due_report(tmp_path, monkeypatch):
    monkeypatch.setattr(
        policy_runner,
        "list_my_projects",
        lambda *args, **kwargs: [
            {"id": "project-1", "project_name": "Alpha", "user_id": "owner-1"},
            {"id": "project-2", "project_name": "Beta", "user_id": "owner-1"},
        ],
    )
    monkeypatch.setattr(policy_runner, "list_incoming_interests", lambda *args, **kwargs: [{"id": "i1", "status": "open"}])
    monkeypatch.setattr(
        policy_runner,
        "get_policy",
        lambda *args, **kwargs: {
            "project-1": {
                "project_id": "project-1",
                "market_patrol_interval": "10m",
                "message_patrol_interval": "5m",
                "interest_behavior": "direct_send",
                "reply_behavior": "notify_then_send",
                "extra_requirements": "Prefer serious async projects.",
            },
            "project-2": {
                "project_id": "project-2",
                "market_patrol_interval": "manual",
                "message_patrol_interval": "30m",
                "interest_behavior": "notify_then_send",
                "reply_behavior": "direct_send",
                "extra_requirements": "",
            },
        }[kwargs.get("project_id")],
    )

    state_path = tmp_path / "state.json"
    state_path.write_text(
        json.dumps(
            {
                "schema_version": 2,
                "projects": {
                    "project-1": {
                        "last_market_run_at": (datetime(2026, 3, 21, 12, 0, tzinfo=timezone.utc) - timedelta(minutes=11)).isoformat(),
                        "last_message_run_at": (datetime(2026, 3, 21, 12, 0, tzinfo=timezone.utc) - timedelta(minutes=6)).isoformat(),
                        "market_cursor": 20,
                    },
                    "project-2": {
                        "last_market_run_at": None,
                        "last_message_run_at": (datetime(2026, 3, 21, 12, 0, tzinfo=timezone.utc) - timedelta(minutes=5)).isoformat(),
                        "market_cursor": 0,
                    },
                },
                "pending_actions": {
                    "M01": {"token": "M01", "status": "pending_user"},
                },
            }
        ),
        encoding="utf-8",
    )

    summary = policy_runner.run_once(
        agent_key="agent-key",
        state_file=state_path,
        report_dir=tmp_path / "reports",
        now=datetime(2026, 3, 21, 12, 0, tzinfo=timezone.utc),
    )

    assert summary["mode"] == "agent_first_brief"
    assert summary["incoming_interests"] == [{"id": "i1", "status": "open"}]
    assert summary["pending_actions"] == [{"token": "M01", "status": "pending_user"}]

    project_one = summary["projects"][0]
    assert project_one["project_id"] == "project-1"
    assert project_one["policy"]["interest_behavior"] == "direct_send"
    assert project_one["due"]["market"] is True
    assert project_one["due"]["messages"] is True

    project_two = summary["projects"][1]
    assert project_two["project_id"] == "project-2"
    assert project_two["due"]["market"] is False
    assert project_two["due"]["market_reason"] == "manual_interval"
    assert project_two["due"]["messages"] is False

    latest_summary = json.loads((tmp_path / "reports" / "latest-summary.json").read_text(encoding="utf-8"))
    assert latest_summary["projects"][0]["project_id"] == "project-1"
