#!/usr/bin/env python3
"""
Minimal ClawMatch autopilot scaffold.

Purpose:
- run on the agent side, not the website side
- scan market periodically
- skip already-contacted projects
- surface candidate projects worth sending interest to

This is intentionally conservative for early testing.
It defaults to dry-run and only auto-sends interests when explicitly enabled.
"""

import argparse
import json
import sys
from pathlib import Path

import requests

SUPABASE_URL = "https://xjljjxogsxumcnjyetwy.supabase.co"
ANON_KEY = "sb_publishable_dlgv32Zav_IaU_l6LVYu0A_CIz-Ww_u"


def headers(token: str):
    return {
        "apikey": ANON_KEY,
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }


def get_current_user(token: str):
    r = requests.get(f"{SUPABASE_URL}/auth/v1/user", headers=headers(token), timeout=30)
    r.raise_for_status()
    return r.json()


def list_market(token: str, limit: int = 50):
    url = (
        f"{SUPABASE_URL}/rest/v1/projects"
        f"?select=id,user_id,project_name,public_summary,tags,agent_contact,created_at"
        f"&public_summary=not.is.null&order=created_at.desc&limit={limit}"
    )
    r = requests.get(url, headers=headers(token), timeout=30)
    r.raise_for_status()
    return r.json()


def list_open_interests(token: str):
    url = (
        f"{SUPABASE_URL}/rest/v1/interests"
        "?select=id,target_project_id,status,message,created_at"
        "&status=eq.open&order=created_at.desc"
    )
    r = requests.get(url, headers=headers(token), timeout=30)
    r.raise_for_status()
    return r.json()


def tokenize(text: str):
    return {
        word.strip().lower()
        for word in ''.join(ch if ch.isalnum() else ' ' for ch in (text or '')).split()
        if len(word.strip()) > 2
    }


def keyword_overlap(project, policy):
    words = tokenize(project.get('project_name', '') + ' ' + project.get('public_summary', '') + ' ' + (project.get('tags') or ''))
    hard_words = set()
    for item in policy.get('hardConstraints', []):
        hard_words |= tokenize(item)
    return len(words & hard_words)


def submit_interest(token: str, project_id: str, message: str, contact: str | None = None):
    payload = {
        'target_project_id': project_id,
        'message': message,
        'agent_contact': contact,
    }
    r = requests.post(f"{SUPABASE_URL}/rest/v1/interests", headers=headers(token) | {'Prefer': 'return=representation'}, json=payload, timeout=30)
    r.raise_for_status()
    return r.json()


def build_interest_message(project: dict):
    name = project.get('project_name') or 'this project'
    tags = project.get('tags') or ''
    return f"My agent thinks my owner may be a promising fit for {name}. Interested in exploring whether there is a good collaboration fit. Tags noticed: {tags}".strip()


def choose_candidates(token: str, policy: dict):
    me = get_current_user(token)
    market = list_market(token, limit=100)
    open_interests = list_open_interests(token)
    already_open = {row['target_project_id'] for row in open_interests}

    candidates = []
    for project in market:
        if policy.get('interestStrategy', {}).get('skipOwnProjects', True) and project.get('user_id') == me.get('id'):
            continue
        if policy.get('interestStrategy', {}).get('skipIfExistingOpenInterest', True) and project.get('id') in already_open:
            continue

        overlap = keyword_overlap(project, policy)
        min_overlap = policy.get('interestStrategy', {}).get('minKeywordOverlap', 1)
        if overlap < min_overlap:
            continue

        candidates.append({
            'project_id': project.get('id'),
            'project_name': project.get('project_name'),
            'keyword_overlap': overlap,
            'tags': project.get('tags'),
            'summary': project.get('public_summary')
        })

    max_n = int(policy.get('maxNewInterestsPerRun', 3))
    return candidates[:max_n]


def main():
    parser = argparse.ArgumentParser(description='ClawMatch autopilot scaffold')
    parser.add_argument('--token', required=True, help="User's ClawMatch API key / JWT")
    parser.add_argument('--policy', required=True, help='Path to autopilot policy JSON')
    parser.add_argument('--send', action='store_true', help='Actually submit interests instead of dry-run only')
    parser.add_argument('--agent-contact', help='Agent contact to attach when sending interests')
    args = parser.parse_args()

    policy_path = Path(args.policy)
    if not policy_path.exists():
        print(f"Policy file not found: {policy_path}", file=sys.stderr)
        sys.exit(1)

    policy = json.loads(policy_path.read_text())
    candidates = choose_candidates(args.token, policy)

    if not args.send:
        print(json.dumps({
            'mode': 'dry-run',
            'policy': policy,
            'candidates': candidates
        }, indent=2, ensure_ascii=False))
        return

    sent = []
    for candidate in candidates:
        result = submit_interest(
            args.token,
            candidate['project_id'],
            build_interest_message(candidate),
            args.agent_contact,
        )
        sent.append(result)

    print(json.dumps({
        'mode': 'send',
        'sent': sent,
        'count': len(sent)
    }, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    main()
