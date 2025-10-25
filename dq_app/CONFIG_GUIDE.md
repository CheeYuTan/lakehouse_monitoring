# Configuration Guide

## 📊 Dashboard Configuration

The dashboard iframe URL is **fully configurable** through environment variables.

### Method 1: Configure Individual Components (Recommended)

Set these in `app.yaml`:

```yaml
env:
  - name: DATABRICKS_HOST
    value: "e2-demo-field-eng.cloud.databricks.com"
  - name: DATABRICKS_ORG_ID
    value: "1444828305810485"
  - name: DASHBOARD_ID
    value: "01f097746d9d1bbbbc0d7939c55bb781"
```

The app will construct: `https://{HOST}/embed/dashboardsv3/{DASHBOARD_ID}?o={ORG_ID}`

### Method 2: Override Full URL

Set the complete URL directly:

```yaml
env:
  - name: DASHBOARD_URL
    value: "https://your-workspace.cloud.databricks.com/embed/dashboardsv3/your-dashboard-id?o=your-org-id"
```

This overrides the individual components.

---

## 🔄 How to Change Dashboard

### In Databricks Apps (app.yaml):

1. Edit `app.yaml`
2. Change `DASHBOARD_ID` to your new dashboard ID
3. Redeploy the app

### For Local Development:

1. Copy `config.env.example` to `.env`
2. Edit `.env` with your values
3. The app will use these environment variables

---

## 📋 Getting Dashboard Embed URL

1. Open your dashboard in Databricks
2. Click Share → Embed
3. Copy the iframe src
4. Extract the dashboard ID from the URL:
   ```
   https://HOST/embed/dashboardsv3/DASHBOARD_ID?o=ORG_ID
                                   ^^^^^^^^^^^ This part
   ```

---

## 🎯 Example

Your iframe:
```html
<iframe src="https://e2-demo-field-eng.cloud.databricks.com/embed/dashboardsv3/01f097746d9d1bbbbc0d7939c55bb781?o=1444828305810485"></iframe>
```

Extract to:
- `DATABRICKS_HOST`: `e2-demo-field-eng.cloud.databricks.com`
- `DASHBOARD_ID`: `01f097746d9d1bbbbc0d7939c55bb781`
- `DATABRICKS_ORG_ID`: `1444828305810485`

---

## 🔧 All Configuration Options

See `config.py` for full list:

```python
# Dashboard
DASHBOARD_URL          # Full URL (overrides below)
DATABRICKS_HOST        # Workspace hostname
DATABRICKS_ORG_ID      # Organization ID
DASHBOARD_ID           # Dashboard ID

# Metadata Tables
CATALOG                # Unity Catalog name
ADMIN_SCHEMA           # Admin schema
DATA_SCHEMA            # Data schema
OUT_SCHEMA             # Output schema

# SQL Warehouse
DATABRICKS_HTTP_PATH   # SQL Warehouse HTTP path
DATABRICKS_TOKEN       # Access token
```

