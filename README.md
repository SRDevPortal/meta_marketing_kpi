### Meta Marketing KPI

Meta marketing KPI dashboard for ERPNext

### Compatibility

- Supports Frappe/ERPNext `15.x` and `16.x`.
- Requires ERPNext because `Meta Marketing KPI.source` links to `Lead Source`.
- Optional OpenAI answers use `openai_api_key` from site config. Without it, the app falls back to rule-based responses.
- AI filter and analyst endpoints are restricted to `System Manager`.

### Installation

You can install this app using the [bench](https://github.com/frappe/bench) CLI:

```bash
cd $PATH_TO_YOUR_BENCH
bench get-app $URL_OF_THIS_REPO --branch develop
bench install-app meta_marketing_kpi
```

### Contributing

This app uses `pre-commit` for code formatting and linting. Please [install pre-commit](https://pre-commit.com/#installation) and enable it for this repository:

```bash
cd apps/meta_marketing_kpi
pre-commit install
```

Pre-commit is configured to use the following tools for checking and formatting your code:

- ruff
- eslint
- prettier
- pyupgrade

### License

mit
