"""NYAYA.ai self-test.  Run from the backend folder:   python selftest.py

Uses a temporary database and FastAPI's TestClient, so you do NOT need to start
the server first. It checks every API endpoint, error handling and PDF rules.

AI plumbing is tested with a stand-in so the result is repeatable. The LAST
section makes a REAL call to the AI provider and reports honestly whether it worked.
"""
import os
import sys
import tempfile

os.environ["DB_PATH"] = os.path.join(tempfile.mkdtemp(), "selftest.db")  # must be set before imports

import fitz  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

import main  # noqa: E402
from services import ai_service  # noqa: E402

passed = failed = 0


def check(name, cond, extra=""):
    global passed, failed
    if cond:
        passed += 1
        print(f"  PASS  {name}")
    else:
        failed += 1
        print(f"  FAIL  {name} {extra}")


def make_pdf(text=None) -> bytes:
    doc = fitz.open()
    page = doc.new_page()
    if text:
        page.insert_text((72, 72), text)
    data = doc.tobytes()
    doc.close()
    return data


with TestClient(main.app) as c:
    print("\n[1] Health, auth")
    check("GET /api/health", c.get("/api/health").json()["status"] == "ok")
    r = c.post("/api/auth/register", json={"name": "Test Admin", "email": "admin@nyaya.ai", "password": "secret1"})
    check("register admin", r.status_code == 200 and r.json()["user"]["is_admin"], r.text)
    admin_h = {"Authorization": "Bearer " + r.json()["token"]}
    r = c.post("/api/auth/register", json={"name": "Normal User", "email": "user@example.com", "password": "secret1"})
    user_h = {"Authorization": "Bearer " + r.json()["token"]}
    check("duplicate e-mail rejected (409)", c.post("/api/auth/register", json={"name": "X Y", "email": "user@example.com", "password": "secret1"}).status_code == 409)
    check("bad password rejected (401)", c.post("/api/auth/login", json={"email": "user@example.com", "password": "nope"}).status_code == 401)
    check("login ok", c.post("/api/auth/login", json={"email": "user@example.com", "password": "secret1"}).status_code == 200)
    check("chat without login -> 401", c.post("/api/chat", json={"message": "hi"}).status_code == 401)

    print("\n[2] Legal data and search")
    cats = c.get("/api/legal/categories").json()["categories"]
    check("7 categories incl. the 6 required", len(cats) == 7 and {"fundamental", "consumer", "women", "cyber", "labour", "tenant"} <= {x["id"] for x in cats})
    s = c.get("/api/legal/search", params={"q": "right to privacy"}, headers=user_h).json()
    check("search finds Puttaswamy", any("Puttaswamy" in x["title"] for x in s["results"]))
    check("result has title/court/year/source", all(k in s["results"][0] for k in ("title", "court", "year", "source_url")))
    s = c.get("/api/legal/search", params={"q": "zzzqqq nonexistent"}).json()
    check("unknown topic -> empty + notice (no fake case)", s["results"] == [] and s["notice"])
    check("search too short -> 422", c.get("/api/legal/search", params={"q": "a"}).status_code == 422)

    print("\n[3] Chat (AI replaced by a stand-in, plus demo mode)")
    real_cc = ai_service.chat_completion

    def boom(*a, **k):
        raise ai_service.AIServiceError("simulated outage")

    ai_service.chat_completion = boom
    r = c.post("/api/chat", json={"message": "What are tenant rights?"}, headers=user_h)
    check("AI failure -> 503 AI_UNAVAILABLE (not faked)", r.status_code == 503 and r.json()["detail"]["code"] == "AI_UNAVAILABLE", r.text)
    check("failed chat saved nothing", c.get("/api/history", headers=user_h).json()["conversations"] == [])

    ai_service.chat_completion = lambda *a, **k: "STAND-IN ANSWER"
    r = c.post("/api/chat", json={"message": "My landlord won't return my deposit"}, headers=user_h)
    check("chat 200 + category detected", r.status_code == 200 and r.json()["category"] == "tenant" and r.json()["answer"] == "STAND-IN ANSWER", r.text)
    cid = r.json()["conversation_id"]
    r = c.post("/api/chat", json={"message": "and if he refuses?", "conversation_id": cid}, headers=user_h)
    check("follow-up in same conversation", r.status_code == 200 and r.json()["conversation_id"] == cid)
    check("other user cannot use my conversation (404)", c.post("/api/chat", json={"message": "x", "conversation_id": cid}, headers=admin_h).status_code == 404)
    r = c.post("/api/chat", json={"message": "cyber fraud UPI scam", "demo": True}, headers=user_h)
    check("demo mode labelled & works", r.status_code == 200 and "DEMO MODE" in r.json()["answer"] and r.json()["demo"] is True)
    check("empty message -> 422", c.post("/api/chat", json={"message": ""}, headers=user_h).status_code == 422)
    ai_service.chat_completion = real_cc

    print("\n[4] Documents")
    ai_service.chat_completion = lambda *a, **k: "STAND-IN ANALYSIS"
    good = make_pdf("This Rent Agreement is made on 1 January 2025 between the Landlord and the Tenant. The monthly rent is Rs 10000.")
    r = c.post("/api/documents/analyze", files={"file": ("rent.pdf", good, "application/pdf")}, headers=user_h)
    check("text PDF analysed", r.status_code == 200 and r.json()["analysis"] == "STAND-IN ANALYSIS" and r.json()["pages"] == 1, r.text)
    r = c.post("/api/documents/analyze", files={"file": ("scan.pdf", make_pdf(), "application/pdf")}, headers=user_h)
    check("scanned/blank PDF -> 422 clear message", r.status_code == 422 and "scanned" in r.json()["detail"].lower(), r.text)
    check("non-PDF extension -> 415", c.post("/api/documents/analyze", files={"file": ("a.txt", b"hello", "text/plain")}, headers=user_h).status_code == 415)
    check("fake .pdf -> 415", c.post("/api/documents/analyze", files={"file": ("a.pdf", b"not a pdf at all", "application/pdf")}, headers=user_h).status_code == 415)
    big = b"%PDF-1.4" + b"0" * (11 * 1024 * 1024)
    check("oversized file -> 413", c.post("/api/documents/analyze", files={"file": ("big.pdf", big, "application/pdf")}, headers=user_h).status_code == 413)
    ai_service.chat_completion = boom
    r = c.post("/api/documents/analyze", files={"file": ("rent.pdf", good, "application/pdf")}, headers=user_h)
    check("AI failure on document -> 503", r.status_code == 503)
    ai_service.chat_completion = real_cc

    print("\n[5] History, dashboard, admin")
    r = c.post("/api/history/save", json={"title": "Deposit", "content": "Some answer", "category": "tenant"}, headers=user_h)
    check("save answer", r.status_code == 200)
    h = c.get("/api/history", headers=user_h).json()
    check("history has conversations/saved/documents/searches", len(h["conversations"]) >= 1 and len(h["saved"]) == 1 and len(h["documents"]) == 1 and len(h["searches"]) >= 1)
    check("load conversation messages", len(c.get(f"/api/history/conversations/{cid}", headers=user_h).json()["messages"]) == 4)
    check("delete saved", c.delete(f"/api/history/saved/{h['saved'][0]['id']}", headers=user_h).status_code == 200)
    st = c.get("/api/dashboard/stats", headers=user_h).json()
    check("user stats", st["conversations"] >= 1 and st["documents"] == 1)
    check("profile update", c.patch("/api/auth/me", json={"language": "hi"}, headers=user_h).json()["language"] == "hi")
    check("admin stats as admin", c.get("/api/admin/stats", headers=admin_h).json()["total_users"] == 2)
    check("admin stats as normal user -> 403", c.get("/api/admin/stats", headers=user_h).status_code == 403)
    tc = c.get("/api/admin/stats", headers=admin_h).json()["top_categories"]
    check("most-searched categories populated", len(tc) >= 1)

    print("\n[6] Frontend served")
    check("GET / (landing page)", c.get("/").status_code == 200 and "NYAYA" in c.get("/").text)
    check("GET /app.html", c.get("/app.html").status_code == 200)

print(f"\n{passed} passed, {failed} failed")

print("\n[7] REAL AI provider check (informational; needs internet)")
st = ai_service.check_status()
print("  base_url :", st["base_url"], "| model:", st["model"])
if st["available"]:
    print("  /models  : reachable. Models:", ", ".join(st["models"][:8]) or "(none listed)")
    print("  model listed:", st["model_listed"])
    try:
        out = ai_service.chat_completion([{"role": "user", "content": "Reply with the single word: ready"}])
        print("  chat call: SUCCESS ->", out[:80])
    except ai_service.AIServiceError as e:
        print("  chat call: FAILED ->", e, "\n  (App will show this error; use Demo mode.)")
else:
    print("  AI provider NOT reachable:", st["error"], "\n  (App will show a clear error and offer Demo mode.)")

sys.exit(1 if failed else 0)
