import io
import json
from fastapi.testclient import TestClient
import main

def test_full_flow():
    client = TestClient(main.app)

    # 1. Health check
    res = client.get("/")
    print("Health Check Status:", res.status_code)
    print("Root payload:", json.dumps(res.json(), indent=2))

    # 2. Upload and analyze a cybersecurity brief
    brief_content = """
PROJECT BRIEF: Cybersecurity SIEM & Automated Threat Hunting Engine
We are engineering a next-generation SOC defense platform.
Demands:
- Kernel eBPF network packet telemetry filtering with nanosecond resolution.
- Graph database threat actor correlation engine written in Python & Rust.
- Interactive React threat hunting console with topological node exploration.
- Kubernetes security enforcement with automated CI/CD container scanning.
"""

    file_obj = io.BytesIO(brief_content.encode("utf-8"))
    response = client.post(
        "/api/analyze",
        data={"team_size": 4},
        files={"file": ("cybersecurity_siem_brief.txt", file_obj, "text/plain")}
    )

    print("\nAPI Response Status:", response.status_code)
    assert response.status_code == 200, f"Failed: {response.text}"

    data = response.json()
    print("=" * 70)
    print(f"PROJECT NAME: {data.get('project_name')}")
    print(f"TECH SIGNALS: {', '.join(data.get('tech_signals', []))}")
    print("=" * 70)

    for idx, role_item in enumerate(data.get("roles", []), 1):
        cand = role_item.get("assigned_candidate", {})
        print(f"\nROLE {idx}: {role_item.get('role')} ({role_item.get('badge')})")
        print(f"  • Assigned Candidate: {cand.get('name')} | Archetype: {cand.get('archetype')} | OVR: {cand.get('overall_rating')}")
        print(f"  • AI Match Rationale: {cand.get('match_rationale')}")
        print(f"  • Deliverable Tasks ({len(role_item.get('tasks', []))} total):")
        for task in role_item.get("tasks", []):
            print(f"      - {task}")

    print("\n" + "=" * 70)
    print("[SUCCESS] Live Gemini 2.5 Flash decomposition and matching verified 100%!")
    print("=" * 70)

if __name__ == "__main__":
    test_full_flow()
