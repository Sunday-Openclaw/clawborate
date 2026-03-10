import sys
import argparse
import requests
import json

SUPABASE_URL = "https://xjljjxogsxumcnjyetwy.supabase.co"
ANON_KEY = "sb_publishable_dlgv32Zav_IaU_l6LVYu0A_CIz-Ww_u"


def get_headers(token):
    return {
        "apikey": ANON_KEY,
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }


def update_project(token, project_id, summary, constraints, tags, contact):
    url = f"{SUPABASE_URL}/rest/v1/projects?id=eq.{project_id}"
    payload = {
        "public_summary": summary,
        "private_constraints": constraints,
        "tags": tags,
        "agent_contact": contact,
    }

    try:
        res = requests.patch(url, headers=get_headers(token), json=payload, timeout=30)
        res.raise_for_status()
        print(f"✅ Success! Updated Project {project_id}.")
        return res.json()
    except Exception as e:
        print(f"❌ Error updating project: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(e.response.text)
        sys.exit(1)


def fetch_project(token, project_id):
    url = f"{SUPABASE_URL}/rest/v1/projects?id=eq.{project_id}&select=id,project_name,public_summary,tags,agent_contact,created_at"
    res = requests.get(url, headers=get_headers(token), timeout=30)
    res.raise_for_status()
    data = res.json()
    if not data:
        raise ValueError(f"Project not found: {project_id}")
    return data[0]


def submit_evaluation(token, project_id, score, confidence, reason, should_connect):
    payload = {
        "target_project_id": project_id,
        "score": int(score),
        "confidence": float(confidence),
        "reason": reason,
        "should_connect": bool(should_connect),
    }
    url = f"{SUPABASE_URL}/rest/v1/evaluations"
    try:
        res = requests.post(url, headers=get_headers(token), json=payload, timeout=30)
        res.raise_for_status()
        print(f"✅ Success! Submitted evaluation for Project {project_id}.")
        return res.json()
    except Exception as e:
        print(f"❌ Error submitting evaluation: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(e.response.text)
        sys.exit(1)


def evaluate_project(token, project_id, score, confidence, reason, should_connect):
    project = fetch_project(token, project_id)
    print("📌 Target Project")
    print(json.dumps(project, indent=2, ensure_ascii=False))
    print()
    return submit_evaluation(token, project_id, score, confidence, reason, should_connect)


def main():
    parser = argparse.ArgumentParser(description="ClawMatch Agent Tool")
    parser.add_argument("action", choices=["update", "create", "evaluate", "get-project"], help="Action to perform")
    parser.add_argument("--token", required=True, help="Human's ClawMatch API Key (JWT)")
    parser.add_argument("--id", help="Project ID")
    parser.add_argument("--summary", help="Public Billboard summary")
    parser.add_argument("--constraints", help="Private Whisper constraints")
    parser.add_argument("--tags", help="Comma separated tags")
    parser.add_argument("--contact", help="Agent contact info (e.g. @bot)")
    parser.add_argument("--score", type=int, help="Evaluation score 0-100")
    parser.add_argument("--confidence", type=float, help="Evaluation confidence 0-1")
    parser.add_argument("--reason", help="Short private explanation for the owner")
    parser.add_argument("--should-connect", choices=["true", "false"], help="Whether the agent recommends reaching out")

    args = parser.parse_args()

    if args.action == "update":
        if not args.id:
            print("❌ --id is required for update")
            sys.exit(1)
        update_project(args.token, args.id, args.summary, args.constraints, args.tags, args.contact)
    elif args.action == "get-project":
        if not args.id:
            print("❌ --id is required for get-project")
            sys.exit(1)
        project = fetch_project(args.token, args.id)
        print(json.dumps(project, indent=2, ensure_ascii=False))
    elif args.action == "evaluate":
        missing = [
            name for name, value in {
                "--id": args.id,
                "--score": args.score,
                "--confidence": args.confidence,
                "--reason": args.reason,
                "--should-connect": args.should_connect,
            }.items() if value is None
        ]
        if missing:
            print("❌ Missing required arguments for evaluate:", ", ".join(missing))
            sys.exit(1)
        evaluate_project(
            args.token,
            args.id,
            args.score,
            args.confidence,
            args.reason,
            args.should_connect == "true",
        )
    else:
        print("Action not fully implemented yet in CLI.")


if __name__ == "__main__":
    main()
