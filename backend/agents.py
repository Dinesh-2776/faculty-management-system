"""
GenAI layer.
  1) Single agent : ONE assistant that decides which database tools to call (tool use / function calling).
  2) Multi agent  : THREE specialised agents (Workload, Leave, Coordinator) that pass reports to each other.
If ANTHROPIC_API_KEY is missing, both run in demo mode using plain Python so the app still works.
"""
import os
import json
from datetime import date
import models

MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")


def _client():
    key = os.getenv("ANTHROPIC_API_KEY")
    if not key:
        return None
    import anthropic
    return anthropic.Anthropic(api_key=key)


# ---------------------------------------------------------------- data tools
def tool_list_faculty(db, department=None):
    out = []
    for f in db.query(models.Faculty).all():
        if department and f.department.name.lower() != department.lower():
            continue
        out.append({"id": f.id, "name": f.name, "designation": f.designation,
                    "department": f.department.name, "email": f.email})
    return out


def tool_workload(db):
    res = []
    for f in db.query(models.Faculty).all():
        hrs = sum(c.hours_per_week or 0 for c in f.courses)
        mx = f.max_hours_per_week or 1
        res.append({"faculty": f.name, "department": f.department.name,
                    "courses": [c.code for c in f.courses], "assigned_hours": hrs,
                    "max_hours": mx, "utilization_pct": round(100 * hrs / mx)})
    return res


def tool_leaves(db, status=None):
    res = []
    for l in db.query(models.LeaveRequest).all():
        if status and l.status.lower() != status.lower():
            continue
        res.append({"id": l.id, "faculty": l.faculty.name, "from": str(l.start_date), "to": str(l.end_date),
                    "reason": l.reason, "status": l.status,
                    "courses_affected": [c.code for c in l.faculty.courses]})
    return res


def tool_unassigned_courses(db):
    return [{"code": c.code, "title": c.title, "hours_per_week": c.hours_per_week}
            for c in db.query(models.Course).filter(models.Course.faculty_id.is_(None)).all()]


TOOL_FUNCS = {
    "list_faculty": tool_list_faculty,
    "get_workload": lambda db: tool_workload(db),
    "get_leaves": tool_leaves,
    "get_unassigned_courses": lambda db: tool_unassigned_courses(db),
}

TOOLS = [
    {"name": "list_faculty", "description": "List faculty members, optionally filtered by department name.",
     "input_schema": {"type": "object", "properties": {"department": {"type": "string"}}}},
    {"name": "get_workload", "description": "Weekly teaching hours, courses and utilization % for every faculty member.",
     "input_schema": {"type": "object", "properties": {}}},
    {"name": "get_leaves", "description": "Leave requests, optionally filtered by status (Pending, Approved, Rejected).",
     "input_schema": {"type": "object", "properties": {"status": {"type": "string"}}}},
    {"name": "get_unassigned_courses", "description": "Courses that currently have no faculty assigned.",
     "input_schema": {"type": "object", "properties": {}}},
]

SINGLE_SYSTEM = (
    "You are the Faculty Assistant for a college. Use the tools to fetch real data before answering. "
    "Never invent faculty, courses or numbers. Keep answers short and clear. Today is " + date.today().isoformat() + "."
)


# ---------------------------------------------------------------- single agent
def run_single_agent(db, question):
    client = _client()
    if client is None:
        w = tool_workload(db)
        top = max(w, key=lambda x: x["utilization_pct"])
        return {"mode": "demo", "steps": ["(demo) read workload table"],
                "answer": f"DEMO MODE (no API key). Most loaded faculty: {top['faculty']} at "
                          f"{top['utilization_pct']}% utilization. Add ANTHROPIC_API_KEY to .env for real AI answers."}

    messages = [{"role": "user", "content": question}]
    steps = []
    for _ in range(6):  # safety limit on the agent loop
        resp = client.messages.create(model=MODEL, max_tokens=1000, system=SINGLE_SYSTEM,
                                      tools=TOOLS, messages=messages)
        if resp.stop_reason == "tool_use":
            messages.append({"role": "assistant", "content": resp.content})
            results = []
            for block in resp.content:
                if block.type == "tool_use":
                    data = TOOL_FUNCS[block.name](db, **block.input)
                    steps.append(f"Called tool: {block.name}({json.dumps(block.input)})")
                    results.append({"type": "tool_result", "tool_use_id": block.id,
                                    "content": json.dumps(data, default=str)})
            messages.append({"role": "user", "content": results})
        else:
            text = "".join(b.text for b in resp.content if b.type == "text")
            return {"mode": "live", "steps": steps, "answer": text}
    return {"mode": "live", "steps": steps, "answer": "Stopped: too many tool calls."}


# ---------------------------------------------------------------- multi agent
def _ask(client, system, content):
    r = client.messages.create(model=MODEL, max_tokens=700, system=system,
                               messages=[{"role": "user", "content": content}])
    return "".join(b.text for b in r.content if b.type == "text")


def run_multi_agent(db, goal):
    workload, leaves, unassigned = tool_workload(db), tool_leaves(db), tool_unassigned_courses(db)
    client = _client()
    if client is None:
        over = [w["faculty"] for w in workload if w["utilization_pct"] > 100]
        return {"mode": "demo", "agents": [
            {"name": "Workload Agent", "output": f"(demo) Overloaded: {over or 'none'}"},
            {"name": "Leave Agent", "output": f"(demo) {len(leaves)} leave requests found"},
            {"name": "Coordinator Agent",
             "output": f"(demo) {len(unassigned)} courses unassigned. Add ANTHROPIC_API_KEY for the real multi-agent run."}]}

    a1 = _ask(client,
              "You are the Workload Agent. Analyse teaching load. Flag anyone above 90% utilization and anyone "
              "below 50%. Max 120 words, bullet points.",
              f"Goal: {goal}\nWorkload: {json.dumps(workload)}\nUnassigned courses: {json.dumps(unassigned)}")
    a2 = _ask(client,
              "You are the Leave Agent. Review leave requests, point out which courses would be uncovered, "
              "and state any risk of clashing leaves. Max 120 words, bullet points.",
              f"Goal: {goal}\nLeaves: {json.dumps(leaves)}")
    a3 = _ask(client,
              "You are the Coordinator Agent. Combine the two reports into a final action plan: who should "
              "take unassigned courses, which leaves to approve/reject and why. Max 180 words.",
              f"Goal: {goal}\n\nWorkload report:\n{a1}\n\nLeave report:\n{a2}\n\nUnassigned: {json.dumps(unassigned)}\n"
              f"Workload data: {json.dumps(workload)}")
    return {"mode": "live", "agents": [{"name": "Workload Agent", "output": a1},
                                       {"name": "Leave Agent", "output": a2},
                                       {"name": "Coordinator Agent", "output": a3}]}
