from __future__ import annotations

import re

import frappe
import requests


def _ensure_solution_prefix(text: str) -> str:
    out = (text or "").strip()
    if not out:
        return "Here is the solution:\nNo answer returned."
    if out.lower().startswith("here is the solution:"):
        return out
    return f"Here is the solution:\n{out}"


def _normalize_currency_to_inr(text: str) -> str:
    out = text or ""
    out = re.sub(r"\$\s*([0-9][0-9,]*(?:\.\d+)?)", r"₹\1", out)
    out = re.sub(r"\bUSD\b", "INR", out, flags=re.IGNORECASE)
    return out


def _response_mode(question: str) -> str:
    q = (question or "").strip().lower()
    if not q:
        return "detailed"
    if "single word" in q or "one word" in q:
        return "single_word"
    if re.search(r"\bhow many\b|\bcount\b|\btotal\b", q):
        return "short_metric"
    if len(q.split()) <= 6:
        return "short_metric"
    return "detailed"


def _build_format_instruction(question: str) -> str:
    mode = _response_mode(question)
    if mode == "single_word":
        return (
            "If the user asks for one/single-word verdict, return exactly one word after prefix: "
            "Good or Bad. No bullets, no sections, no extra sentence."
        )
    if mode == "short_metric":
        return (
            "Keep answer very short: 1-2 lines max, directly answering the asked metric/question "
            "with exact numbers from context. Do not include template sections."
        )
    return (
        "Use markdown sections only for deep analysis questions:\n"
        "### Verdict\n### Why (with metrics)\n### Action Plan (3-5 bullet steps)\n### Next Checkpoint"
    )


def answer_meta_contextual_question(question: str, context: dict) -> dict:
    answer = _answer_with_openai(question, context, "You are a senior Meta Ads campaign performance analyst.")
    if answer:
        return answer
    return {
        "answer": _ensure_solution_prefix(
            "Meta campaign performance is weak if clicks or leads are flat while spend is increasing. "
            "Check CTR, CPC, and cost per lead trend, then update creative and audience targeting in small controlled steps."
        ),
        "confidence": 0.58,
    }


def _answer_with_openai(question: str, context: dict, role_hint: str) -> dict | None:
    api_key = frappe.conf.get("openai_api_key")
    if not api_key:
        return None

    prompt = (
        f"{role_hint} Answer using only the provided KPI context. "
        "Do not give generic advice. Use campaign-specific numbers from context and mention at least 3 metrics. "
        "ALWAYS start with: 'Here is the solution:'\n"
        f"{_build_format_instruction(question)}\n"
        "All monetary values must be shown in INR (rupees), never dollars. Use ₹ symbol for currency amounts.\n"
        "If data is missing, explicitly state which metric is unavailable."
        f"\nQuestion: {question}"
        f"\nContext: {context}"
    )

    try:
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": "gpt-4o-mini",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.2,
            },
            timeout=20,
        )
        response.raise_for_status()
        body = response.json()
        content = body.get("choices", [{}])[0].get("message", {}).get("content")
        if not content:
            return None
        inr_content = _normalize_currency_to_inr(content)
        return {"answer": _ensure_solution_prefix(inr_content), "confidence": 0.86}
    except Exception:
        frappe.log_error(frappe.get_traceback(), "OpenAI meta analyst call failed")
        return None
