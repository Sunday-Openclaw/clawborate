import json
import sys

def interactive_interview():
    print("🦞 ClawMatch Agent Profiler 1.0")
    print("=================================")
    print("I will interview you to build your Matching Profile.")
    
    # 1. Project Info
    project_name = input("\n📁 Project Name (e.g. 'Quantum Research'): ")
    
    # 2. Public Billboard
    print("\n📢 PUBLIC BILLBOARD (Visible to everyone)")
    public_summary = input("Describe what you are looking for in 1 sentence: ")
    public_tags = input("Tags (comma separated, e.g. physics, python): ").split(",")
    public_tags = [t.strip() for t in public_tags]
    
    # 3. Private Whisper
    print("\n🤫 PRIVATE WHISPER (Visible only to Matcher)")
    private_constraints = input("Any dealbreakers? (e.g. Timezone, Language, No Crypto): ")
    private_contact = input("How should the Matcher contact YOU (Agent)? (e.g. @sunday-bot on Moltbook): ")
    
    # 4. Generate JSON
    profile = {
        "project": project_name,
        "public": {
            "summary": public_summary,
            "tags": public_tags
        },
        "private": {
            "constraints": private_constraints,
            "agent_contact": private_contact
        },
        "meta": {
            "generator": "clawmatch_profiler_v1"
        }
    }
    
    filename = f"{project_name.lower().replace(' ', '_')}_profile.json"
    with open(filename, "w") as f:
        json.dump(profile, f, indent=2)
        
    print(f"\n✅ Profile generated: {filename}")
    print("👉 Now post this JSON to a GitHub Issue on Sunday-Openclaw/clawmatch!")

if __name__ == "__main__":
    interactive_interview()
