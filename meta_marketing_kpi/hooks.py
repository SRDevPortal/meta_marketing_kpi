app_name = "meta_marketing_kpi"
app_title = "Meta Marketing KPI"
app_publisher = "SAI"
app_description = "Meta marketing KPI dashboard for ERPNext"
app_email = "sai@example.com"
app_license = "mit"

required_apps = ["erpnext"]

# Workspace and reports are exported as standard app files.
fixtures = []

before_install = "meta_marketing_kpi.install.before_install"
after_install = "meta_marketing_kpi.install.after_install"
after_migrate = "meta_marketing_kpi.install.after_migrate"

doctype_js = {
    "Meta Marketing KPI": "meta_marketing_kpi/doctype/meta_marketing_kpi/meta_marketing_kpi.js",
}

doctype_list_js = {
    "Meta Marketing KPI": "meta_marketing_kpi/doctype/meta_marketing_kpi/meta_marketing_kpi_list.js",
}
