app_name = "meta_marketing_kpi"
app_title = "Meta Marketing KPI"
app_publisher = "SAI"
app_description = "Meta marketing KPI dashboard for ERPNext"
app_email = "sai@example.com"
app_license = "mit"

fixtures = [
    {
        "dt": "Workspace",
        "filters": [["module", "=", "Meta Marketing KPI"]],
    },
    {
        "dt": "Report",
        "filters": [["module", "=", "Meta Marketing KPI"]],
    },
]

before_install = "meta_marketing_kpi.install.before_install"
after_install = "meta_marketing_kpi.install.after_install"
after_migrate = "meta_marketing_kpi.install.after_migrate"
