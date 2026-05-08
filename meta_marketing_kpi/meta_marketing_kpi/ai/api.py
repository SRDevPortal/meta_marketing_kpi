from __future__ import annotations

import json

import frappe
from frappe.utils import flt

from meta_marketing_kpi.meta_marketing_kpi.ai.llm_analyst import answer_meta_contextual_question


MANAGER_ROLE = "System Manager"


def _require_manager() -> None:
    frappe.only_for(MANAGER_ROLE)


def _normalize_campaign_selection(campaign_names: list[str] | str | None) -> list[str]:
    if not campaign_names:
        return []

    parsed = campaign_names
    if isinstance(campaign_names, str):
        try:
            parsed = frappe.parse_json(campaign_names)
        except Exception:
            try:
                parsed = json.loads(campaign_names)
            except Exception:
                parsed = [item.strip() for item in campaign_names.split(",") if item.strip()]

    normalized: list[str] = []
    if isinstance(parsed, dict):
        # Some UI widgets return {"Campaign A": 1, "Campaign B": 0}
        for key, value in parsed.items():
            if value:
                normalized.append(str(key).strip())
    elif isinstance(parsed, list):
        for item in parsed:
            if isinstance(item, dict):
                # Support [{"value":"X","checked":1}] or {"label":"X","checked":1}
                if item.get("checked") is False or item.get("checked") == 0:
                    continue
                candidate = item.get("value") or item.get("label") or item.get("name")
                if candidate:
                    normalized.append(str(candidate).strip())
            else:
                val = str(item).strip()
                if val:
                    normalized.append(val)

    # Keep order, drop duplicates
    out: list[str] = []
    for name in normalized:
        if name and name not in out:
            out.append(name)
    return out


@frappe.whitelist()
def get_meta_filter_options() -> dict:
    _require_manager()
    account_rows = frappe.get_all(
        "Meta Marketing KPI",
        fields=["account_name"],
        filters={"account_name": ["is", "set"]},
        group_by="account_name",
        order_by="account_name asc",
    )
    campaign_rows = frappe.get_all(
        "Meta Marketing KPI",
        fields=["account_name", "campaign_name"],
        filters={"account_name": ["is", "set"], "campaign_name": ["is", "set"]},
        order_by="account_name asc, campaign_name asc",
    )
    account_campaigns_map: dict[str, list[str]] = {}
    campaign_names: set[str] = set()
    for row in campaign_rows:
        account = (row.get("account_name") or "").strip()
        campaign = (row.get("campaign_name") or "").strip()
        if not account or not campaign:
            continue
        campaign_names.add(campaign)
        account_campaigns_map.setdefault(account, [])
        if campaign not in account_campaigns_map[account]:
            account_campaigns_map[account].append(campaign)
    return {
        "account_names": [row.get("account_name") for row in account_rows if row.get("account_name")],
        "campaign_names": sorted(campaign_names),
        "account_campaigns_map": account_campaigns_map,
    }


@frappe.whitelist()
def ask_meta_campaign_ai(
    account_name: str,
    question: str,
    campaign_name: str | None = None,
    campaign_names: list[str] | str | None = None,
    days: int = 60,
) -> dict:
    _require_manager()
    normalized_account = (account_name or "").strip()
    filters: dict = {"account_name": normalized_account}

    selected_campaign_names = _normalize_campaign_selection(campaign_names)

    # Protect against mixed-account selections from UI by intersecting with account's campaigns.
    valid_campaign_rows = frappe.get_all(
        "Meta Marketing KPI",
        fields=["campaign_name"],
        filters={"account_name": normalized_account, "campaign_name": ["is", "set"]},
        group_by="campaign_name",
        order_by="campaign_name asc",
    )
    valid_campaigns = {(row.get("campaign_name") or "").strip() for row in valid_campaign_rows if row.get("campaign_name")}
    if selected_campaign_names:
        selected_campaign_names = [name for name in selected_campaign_names if name in valid_campaigns]

    analyze_all_campaigns = (campaign_name or "").strip().lower() in {"all", "*"}
    if selected_campaign_names:
        filters["campaign_name"] = ["in", selected_campaign_names]
        analyze_all_campaigns = False
    elif not analyze_all_campaigns and (campaign_name or "").strip():
        filters["campaign_name"] = (campaign_name or "").strip()

    rows = frappe.get_all(
        "Meta Marketing KPI",
        fields=[
            "kpi_date",
            "account_name",
            "campaign_id",
            "campaign_name",
            "impressions",
            "clicks",
            "spend",
            "leads",
            "messaging_conversations_started",
            "messaging_first_reply",
            "cost_per_first_reply",
            "ctr",
            "cpc",
            "cpm",
            "cost_per_lead",
        ],
        filters=filters,
        order_by="kpi_date desc",
        limit=max(14, int(days)),
    )
    if not rows:
        scope = "selected account" if analyze_all_campaigns else "selected campaign/account"
        frappe.throw(f"No Meta Marketing KPI records found for {scope}.")

    recent = rows[:7]
    previous = rows[7:14]

    def aggregate(items: list[dict]) -> dict:
        impressions = sum(flt(item.get("impressions")) for item in items)
        clicks = sum(flt(item.get("clicks")) for item in items)
        spend = sum(flt(item.get("spend")) for item in items)
        leads = sum(flt(item.get("leads")) for item in items)
        conversations = sum(flt(item.get("messaging_conversations_started")) for item in items)
        first_replies = sum(flt(item.get("messaging_first_reply")) for item in items)
        return {
            "impressions": impressions,
            "clicks": clicks,
            "spend": round(spend, 2),
            "leads": round(leads, 2),
            "messaging_conversations_started": round(conversations, 2),
            "messaging_first_reply": round(first_replies, 2),
            "ctr": round((clicks / impressions) * 100, 3) if impressions else 0,
            "cpc": round((spend / clicks), 2) if clicks else 0,
            "cpl": round((spend / leads), 2) if leads else 0,
            "lead_rate": round((leads / clicks) * 100, 3) if clicks else 0,
        }

    recent_summary = aggregate(recent)
    previous_summary = aggregate(previous) if previous else {}
    deltas = {}
    if previous_summary:
        for key in ("impressions", "clicks", "spend", "leads", "ctr", "cpc", "cpl", "lead_rate"):
            deltas[key] = round(flt(recent_summary.get(key)) - flt(previous_summary.get(key)), 3)

    latest_points = [
        {
            "date": row.get("kpi_date"),
            "campaign_name": row.get("campaign_name"),
            "impressions": flt(row.get("impressions")),
            "clicks": flt(row.get("clicks")),
            "spend": round(flt(row.get("spend")), 2),
            "leads": round(flt(row.get("leads")), 2),
            "messaging_conversations_started": flt(row.get("messaging_conversations_started")),
            "messaging_first_reply": flt(row.get("messaging_first_reply")),
            "cost_per_first_reply": round(flt(row.get("cost_per_first_reply")), 2),
            "cost_per_lead": round(flt(row.get("cost_per_lead")), 2),
            "ctr": flt(row.get("ctr")),
            "cpc": flt(row.get("cpc")),
            "cpm": flt(row.get("cpm")),
        }
        for row in rows[:14]
    ]

    context = {
        "account_name": account_name,
        "campaign_name": "All Campaigns" if analyze_all_campaigns else (campaign_name or ""),
        "selected_campaign_names": selected_campaign_names,
        "records_used": len(rows),
        "recent_7_days": recent_summary,
        "previous_7_days": previous_summary,
        "delta_recent_vs_previous": deltas,
        "latest_daily_points": latest_points,
    }
    return answer_meta_contextual_question(question, context)


@frappe.whitelist()
def smoke_meta_campaign_ai(account_name: str | None = None) -> dict:
    """Non-interactive sanity check for the campaign analyst endpoint."""
    _require_manager()
    account = (account_name or "").strip()
    if not account:
        account = frappe.db.get_value("Meta Marketing KPI", {"account_name": ["is", "set"]}, "account_name")
    if not account:
        frappe.throw("No Meta Marketing KPI account_name found to run smoke test.")
    return ask_meta_campaign_ai(
        account_name=account,
        campaign_name="All",
        question="One word verdict: Good or Bad",
        days=30,
    )
