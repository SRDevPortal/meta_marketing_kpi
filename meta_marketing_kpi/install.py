from __future__ import annotations

import frappe


def before_install() -> None:
    if not frappe.db.exists("DocType", "Lead Source"):
        frappe.throw("Meta Marketing KPI requires ERPNext because KPI Source fields link to Lead Source.")


def after_install() -> None:
    clear_meta_cache()


def after_migrate() -> None:
    clear_meta_cache()


def clear_meta_cache() -> None:
    frappe.clear_cache(doctype="Meta Marketing KPI")
    frappe.clear_cache(doctype="Meta Raw Data")
