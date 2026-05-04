from __future__ import annotations

import frappe
from frappe.utils import flt

from meta_marketing_kpi.meta_marketing_kpi.ai.llm_analyst import answer_meta_contextual_question


MANAGER_ROLE = "System Manager"


def _require_manager() -> None:
    frappe.only_for(MANAGER_ROLE)


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
    ad_rows = frappe.get_all(
        "Meta Marketing KPI",
        fields=["ad_name"],
        filters={"ad_name": ["is", "set"]},
        group_by="ad_name",
        order_by="ad_name asc",
    )
    return {
        "account_names": [row.get("account_name") for row in account_rows if row.get("account_name")],
        "ad_names": [row.get("ad_name") for row in ad_rows if row.get("ad_name")],
    }


@frappe.whitelist()
def ask_meta_campaign_ai(
    account_name: str,
    ad_name: str,
    question: str,
    days: int = 60,
) -> dict:
    _require_manager()
    filters = {"account_name": account_name, "ad_name": ad_name}

    rows = frappe.get_all(
        "Meta Marketing KPI",
        fields=["kpi_date", "account_name", "campaign_id", "campaign_name", "ad_name", "impressions", "clicks", "spend", "leads", "ctr", "cpc", "cpm"],
        filters=filters,
        order_by="kpi_date desc",
        limit=max(14, int(days)),
    )
    if not rows:
        frappe.throw("No Meta Marketing KPI records found for selected account/ad.")

    recent = rows[:7]
    previous = rows[7:14]

    def aggregate(items: list[dict]) -> dict:
        impressions = sum(flt(item.get("impressions")) for item in items)
        clicks = sum(flt(item.get("clicks")) for item in items)
        spend = sum(flt(item.get("spend")) for item in items)
        leads = sum(flt(item.get("leads")) for item in items)
        return {
            "impressions": impressions,
            "clicks": clicks,
            "spend": round(spend, 2),
            "leads": round(leads, 2),
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
            "impressions": flt(row.get("impressions")),
            "clicks": flt(row.get("clicks")),
            "spend": round(flt(row.get("spend")), 2),
            "leads": round(flt(row.get("leads")), 2),
            "ctr": flt(row.get("ctr")),
            "cpc": flt(row.get("cpc")),
            "cpm": flt(row.get("cpm")),
        }
        for row in rows[:14]
    ]

    context = {
        "account_name": account_name,
        "ad_name": ad_name,
        "records_used": len(rows),
        "recent_7_days": recent_summary,
        "previous_7_days": previous_summary,
        "delta_recent_vs_previous": deltas,
        "latest_daily_points": latest_points,
    }
    return answer_meta_contextual_question(question, context)
