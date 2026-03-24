from datetime import datetime, timedelta, timezone

from skill_runtime.policy_runtime import db_policy_to_runtime_bundle, should_run_market_patrol, should_run_message_patrol


def test_db_policy_to_runtime_bundle_maps_new_fields_and_legacy_fallbacks():
    bundle = db_policy_to_runtime_bundle(
        {
            "project_id": "project-1",
            "owner_user_id": "owner-1",
            "market_patrol_interval": "30m",
            "message_patrol_interval": "10m",
            "interest_policy": "auto_send_high_confidence",
            "reply_policy": "draft_then_confirm",
            "collaborator_preferences": {
                "priorityTags": ["ai", "biology"],
                "constraints": "avoid crypto; async friendly",
                "preferredWorkingStyle": "async-first",
                "avoidPhrases": ["guaranteed fit"],
                "conversationGoals": ["clarify scope"],
                "conversationAvoid": ["making commitments"],
            },
        }
    )

    effective_policy = bundle["effective_policy"]
    execution = bundle["execution"]

    assert execution["interest_behavior"] == "direct_send"
    assert execution["reply_behavior"] == "notify_then_send"
    assert execution["market_patrol_interval"] == "30m"
    assert execution["message_patrol_interval"] == "10m"
    assert "Prioritize projects or conversations related to: ai, biology." in execution["extra_requirements"]
    assert "Legacy constraints: avoid crypto; async friendly" in execution["extra_requirements"]

    assert effective_policy["agentContext"]["requireAgentJudgment"] is True
    assert "async-first" in effective_policy["agentContext"]["extraRequirements"]
    assert effective_policy["messaging"]["avoidPhrases"] == ["guaranteed fit", "crypto"]
    assert effective_policy["conversationPolicy"]["goals"] == ["clarify scope"]
    assert effective_policy["conversationPolicy"]["avoid"] == ["making commitments"]


def test_should_run_market_and_message_patrol_handle_due_windows():
    now = datetime(2026, 3, 21, 12, 0, tzinfo=timezone.utc)

    assert should_run_market_patrol({"is_active": False}, None, now=now) == (False, "inactive")
    assert should_run_market_patrol({"market_patrol_interval": "manual"}, None, now=now) == (False, "manual_interval")
    assert should_run_market_patrol({"market_patrol_interval": "10m"}, None, now=now) == (True, "first_run")
    assert should_run_market_patrol(
        {"market_patrol_interval": "10m"},
        (now - timedelta(minutes=11)).isoformat(),
        now=now,
    ) == (True, "interval_elapsed")
    assert should_run_market_patrol(
        {"market_patrol_interval": "30m"},
        (now - timedelta(minutes=20)).isoformat(),
        now=now,
    ) == (False, "not_due")

    assert should_run_message_patrol({"message_patrol_interval": "manual"}, None, now=now) == (
        False,
        "manual_interval",
    )
    assert should_run_message_patrol({"message_patrol_interval": "5m"}, None, now=now) == (True, "first_run")
    assert should_run_message_patrol(
        {"message_patrol_interval": "5m"},
        (now - timedelta(minutes=6)).isoformat(),
        now=now,
    ) == (True, "interval_elapsed")
    assert should_run_message_patrol(
        {"message_patrol_interval": "10m"},
        (now - timedelta(minutes=4)).isoformat(),
        now=now,
    ) == (False, "not_due")
