"""Local legal knowledge: categories, keyword classification, retrieval, case index.

Everything returned here comes from the JSON files in backend/data. Nothing is
generated, so nothing here can be a hallucinated judgment or section.
"""
import json
import re
from functools import lru_cache
from urllib.parse import quote_plus

from config import DATA_DIR

DISCLAIMER = (
    "This is general legal information, not legal advice. Laws change and every case is "
    "different. Please consult a qualified advocate for your specific situation."
)

STOPWORDS = {"the", "and", "for", "with", "what", "how", "are", "can", "not", "about", "india",
             "indian", "law", "laws", "act", "case", "cases", "judgment", "judgments", "v", "vs"}

INDIAN_KANOON = "https://indiankanoon.org/search/?formInput="
EXTERNAL_CASE_SOURCES = [
    {"name": "Indian Kanoon", "url": "https://indiankanoon.org/"},
    {"name": "Supreme Court of India", "url": "https://www.sci.gov.in/"},
    {"name": "eCourts Judgments Portal", "url": "https://judgments.ecourts.gov.in/"},
]


@lru_cache(maxsize=1)
def _rights() -> dict:
    return json.loads((DATA_DIR / "rights.json").read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def _cases() -> dict:
    return json.loads((DATA_DIR / "landmark_cases.json").read_text(encoding="utf-8"))


def get_categories() -> dict:
    """Return all legal categories for the Know Your Rights module."""
    data = _rights()
    return {"note": data["note"], "categories": data["categories"]}


def get_category(cat_id: str):
    return next((c for c in _rights()["categories"] if c["id"] == cat_id), None)


def _score(text: str, cat: dict) -> int:
    """Count how many of a category's keywords appear in the text."""
    t = text.lower()
    return sum(1 for k in cat["keywords"] if k.lower() in t)


def classify(text: str):
    """Best-matching category id for a piece of text, or None."""
    best, best_score = None, 0
    for cat in _rights()["categories"]:
        s = _score(text, cat)
        if s > best_score:
            best, best_score = cat["id"], s
    return best


def retrieve_context(text: str, limit: int = 2) -> str:
    """Build a small block of verified reference data to ground the AI's answer."""
    scored = sorted(
        ((_score(text, c), c) for c in _rights()["categories"]), key=lambda x: -x[0]
    )
    parts = []
    for s, cat in scored[:limit]:
        if s == 0:
            continue
        refs = "; ".join(r["label"] for r in cat["references"])
        pts = " ".join(f"- {r['title']}: {r['explanation']}" for r in cat["rights"])
        helps = ", ".join(f"{h['name']} {h['number']}" for h in cat.get("helplines", []))
        parts.append(f"[{cat['title']}] {cat['summary']}\n{pts}\nReferences: {refs}\nHelplines: {helps}")
    return "\n\n".join(parts)


def demo_answer(text: str) -> str:
    """DEMO MODE: answer from the local knowledge base only (no AI model involved)."""
    banner = (
        "> **DEMO MODE - not AI generated.** The AI service was not used. "
        "This answer is a lookup from NYAYA.ai's built-in knowledge base.\n\n"
    )
    cat = get_category(classify(text) or "")
    if not cat:
        names = ", ".join(c["title"] for c in _rights()["categories"])
        return (
            banner
            + "I could not match your question to a topic in the built-in knowledge base.\n\n"
            + f"Topics available in demo mode: {names}.\n\n"
            + "Try again with AI mode, or rephrase using one of these topics.\n\n"
            + f"*{DISCLAIMER}*"
        )
    out = [banner, f"### {cat['title']}\n", cat["summary"] + "\n", "**Key points**\n"]
    out += [f"- **{r['title']}** - {r['explanation']}" for r in cat["rights"]]
    out.append("\n**Legal references**\n")
    out += [f"- {r['label']} ({r['note']})" for r in cat["references"]]
    if cat.get("helplines"):
        out.append("\n**Helplines**\n")
        out += [f"- {h['name']}: {h['number']}" for h in cat["helplines"]]
    out.append("\n**Official sources**\n")
    out += [f"- [{s['name']}]({s['url']})" for s in cat["sources"]]
    out.append(f"\n*{DISCLAIMER}*")
    return "\n".join(out)


def search_cases(query: str) -> dict:
    """Search the curated landmark-case index. Never fabricates results."""
    q = query.strip().lower()
    words = [w for w in re.findall(r"[\w]+", q) if len(w) > 2 and w not in STOPWORDS]
    cat_id = classify(query)
    results = []
    for c in _cases()["cases"]:
        hay = (c["title"] + " " + " ".join(c["topics"])).lower()
        score = sum(2 for w in words if w in hay)
        if q and q in hay:
            score += 3
        # A category-level match only counts when it is the strongest signal we have.
        if cat_id and c["category"] == cat_id and score == 0 and not words:
            score = 1
        if score > 0:
            results.append((score, c))
    results.sort(key=lambda x: (-x[0], -x[1]["year"]))
    out = [
        {
            "title": c["title"],
            "court": c["court"],
            "year": c["year"],
            "category": c["category"],
            "source_name": "Indian Kanoon (search for this judgment)",
            "source_url": INDIAN_KANOON + quote_plus('"' + c["title"] + '"'),
        }
        for _, c in results[:10]
    ]
    notice = (
        None
        if out
        else "No verified result was found in the curated landmark index. "
        "Use the official sources below to search all judgments."
    )
    return {
        "query": query,
        "category": cat_id,
        "results": out,
        "notice": notice,
        "index_note": _cases()["note"],
        "external_sources": [
            {"name": s["name"], "url": s["url"]} for s in EXTERNAL_CASE_SOURCES
        ]
        + [{"name": f"Search '{query}' on Indian Kanoon", "url": INDIAN_KANOON + quote_plus(query)}],
    }
