from __future__ import annotations

import frappe


WORKSPACE_NAME = "Meta Ads KPI"
WORKSPACE_LABEL = "Meta Ads KPI"
WORKSPACE_TITLE = "Meta Ads KPI"
WORKSPACE_MODULE = "Meta Marketing KPI"
LEGACY_WORKSPACE_NAMES = ("Meta Marketing KPI", "Meta Marketing Dashboard")

WORKSPACE_CONTENT = (
    '[{"id":"meta_header","type":"header","data":{"text":"Meta Ads KPI","col":12}},'
    '{"id":"meta_shortcut_1","type":"shortcut","data":{"shortcut_name":"Meta Marketing KPI","col":3}},'
    '{"id":"meta_shortcut_2","type":"shortcut","data":{"shortcut_name":"Meta Raw Data","col":3}},'
    '{"id":"meta_shortcut_3","type":"shortcut","data":{"shortcut_name":"Campaign Performance","col":3}},'
    '{"id":"meta_shortcut_4","type":"shortcut","data":{"shortcut_name":"Ad Performance","col":3}},'
    '{"id":"meta_shortcut_5","type":"shortcut","data":{"shortcut_name":"Account Performance","col":3}}]'
)

WORKSPACE_SHORTCUTS = [
    {
        "color": "Blue",
        "label": "Meta Marketing KPI",
        "type": "URL",
        "url": "/app/meta-marketing-kpi",
    },
    {
        "color": "Green",
        "label": "Meta Raw Data",
        "type": "URL",
        "url": "/app/meta-raw-data",
    },
    {
        "color": "Orange",
        "label": "Campaign Performance",
        "link_to": "Campaign Performance",
        "report_ref_doctype": "Meta Marketing KPI",
        "type": "Report",
    },
    {
        "color": "Purple",
        "label": "Ad Performance",
        "link_to": "Ad Performance",
        "report_ref_doctype": "Meta Marketing KPI",
        "type": "Report",
    },
    {
        "color": "Teal",
        "label": "Account Performance",
        "link_to": "Account Performance",
        "report_ref_doctype": "Meta Marketing KPI",
        "type": "Report",
    },
]


def before_install() -> None:
    if not frappe.db.exists("DocType", "Lead Source"):
        frappe.throw("Meta Marketing KPI requires ERPNext because KPI Source fields link to Lead Source.")


def after_install() -> None:
    ensure_workspace()
    clear_meta_cache()


def after_migrate() -> None:
    ensure_workspace()
    clear_meta_cache()


def clear_meta_cache() -> None:
    frappe.clear_cache(doctype="Meta Marketing KPI")
    frappe.clear_cache(doctype="Meta Raw Data")
    frappe.clear_cache(doctype="Workspace")


def ensure_workspace() -> None:
    if not frappe.db.exists("DocType", "Workspace"):
        return

    migrate_legacy_workspace()
    release_duplicate_workspace_label()

    if not frappe.db.exists("Workspace", WORKSPACE_NAME):
        workspace = frappe.get_doc(
            {
                "doctype": "Workspace",
                "name": WORKSPACE_NAME,
                "label": WORKSPACE_LABEL,
                "title": WORKSPACE_TITLE,
                "module": WORKSPACE_MODULE,
                "public": 1,
                "is_hidden": 0,
                "icon": "chart",
                "content": WORKSPACE_CONTENT,
            }
        )
        for shortcut in WORKSPACE_SHORTCUTS:
            workspace.append("shortcuts", shortcut)
        workspace.insert(ignore_permissions=True)
        return

    frappe.db.set_value(
        "Workspace",
        WORKSPACE_NAME,
        {
            "label": WORKSPACE_LABEL,
            "title": WORKSPACE_TITLE,
            "module": WORKSPACE_MODULE,
            "public": 1,
            "is_hidden": 0,
            "icon": "chart",
            "content": WORKSPACE_CONTENT,
        },
        update_modified=False,
    )
    frappe.db.delete(
        "Workspace Shortcut",
        {
            "parent": WORKSPACE_NAME,
            "parenttype": "Workspace",
            "parentfield": "shortcuts",
        },
    )
    for idx, shortcut in enumerate(WORKSPACE_SHORTCUTS, start=1):
        row = frappe.get_doc(
            {
                "doctype": "Workspace Shortcut",
                "parent": WORKSPACE_NAME,
                "parenttype": "Workspace",
                "parentfield": "shortcuts",
                "idx": idx,
                "doc_view": "",
                **shortcut,
            }
        )
        row.db_insert()


def migrate_legacy_workspace() -> None:
    for workspace_name in LEGACY_WORKSPACE_NAMES:
        if workspace_name == WORKSPACE_NAME or not frappe.db.exists("Workspace", workspace_name):
            continue

        if not frappe.db.exists("Workspace", WORKSPACE_NAME):
            frappe.rename_doc(
                "Workspace",
                workspace_name,
                WORKSPACE_NAME,
                force=True,
            )
            return

        frappe.db.set_value(
            "Workspace",
            workspace_name,
            {
                "label": get_legacy_workspace_label(workspace_name),
                "is_hidden": 1,
                "public": 0,
            },
            update_modified=False,
        )


def release_duplicate_workspace_label() -> None:
    duplicate_workspaces = frappe.get_all(
        "Workspace",
        filters={"label": WORKSPACE_LABEL, "name": ["!=", WORKSPACE_NAME]},
        pluck="name",
    )

    for workspace_name in duplicate_workspaces:
        frappe.db.set_value(
            "Workspace",
            workspace_name,
            {
                "label": get_legacy_workspace_label(workspace_name),
                "is_hidden": 1,
                "public": 0,
            },
            update_modified=False,
        )


def get_legacy_workspace_label(workspace_name: str) -> str:
    base_label = f"{workspace_name} Legacy"
    label = base_label
    counter = 2

    while frappe.db.exists(
        "Workspace",
        {"label": label, "name": ["!=", workspace_name]},
    ):
        label = f"{base_label} {counter}"
        counter += 1

    return label
