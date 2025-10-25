# Configuration Guide

This app is deployed as a **Databricks App** and uses Databricks-native configuration.

## ⚠️ Prerequisites

Before configuring the app, ensure the following are set up:

### 1. **Dashboard Must Be Published**

The dashboard **MUST be published** before you can embed it in the app:

1. Open your dashboard in Databricks
2. Click **Publish** button (top right)
3. Confirm publication
4. Only then can you get the embed URL/Dashboard ID

### 2. **Enable Dashboard Embedding in Workspace**

Dashboard embedding must be allowed at the workspace level:

1. Go to **Settings** (⚙️ icon) → **Workspace admin**
2. Navigate to **Security** tab
3. Under **External access** section
4. Find **Embed dashboards**
5. Set to **"Allow"**
6. Save changes

⚠️ **Without these settings, the dashboard will not load in the app!**

---

## 📋 Configuration Files

### ✅ **`app.yaml`** (Main Configuration)

This is the **only configuration file** you need to modify. It defines:

```yaml
command: [
  "python",
  "app.py"
]

env:
  # Application-specific configuration
  - name: CATALOG
    value: "dbdemos_steventan"
  - name: ADMIN_SCHEMA
    value: "monitoring_admin"
  - name: DATA_SCHEMA
    value: "lakehouse_monitoring"
  - name: OUT_SCHEMA
    value: "lakehouse_monitoring_demo_results"
  - name: SQL_WAREHOUSE_ID
    value: "862f1d757f0424f7"
  - name: DATABRICKS_ORG_ID
    value: "1444828305810485"
  - name: DASHBOARD_ID
    value: "01f097746d9d1bbbbc0d7939c55bb781"
```

### ✅ **Configuration in Code**

Environment variables from `app.yaml` are read directly in `app.py` and `db_utils.py`. No separate config file needed.

## 🔐 Automatic Authentication

The following are **automatically provided** by Databricks Apps ([documentation](https://docs.databricks.com/dev-tools/databricks-apps/system-env#default-environment-variables)):

- ✅ `DATABRICKS_HOST` - Your workspace URL
- ✅ `DATABRICKS_CLIENT_ID` - Service principal client ID
- ✅ `DATABRICKS_CLIENT_SECRET` - OAuth secret
- ✅ `DATABRICKS_WORKSPACE_ID` - Workspace ID
- ✅ `DATABRICKS_APP_NAME` - App name
- ✅ `DATABRICKS_APP_PORT` - Network port

**You do NOT need to define these.** The app uses OAuth authentication automatically.

## 🔄 How to Update Configuration

### 1. **Change Dashboard**

**Prerequisites:**
- ✅ Dashboard must be **published** first
- ✅ Workspace must have **"Embed dashboards" → "Allow"** enabled

Then edit `app.yaml`:

```yaml
- name: DASHBOARD_ID
  value: "your-new-dashboard-id"
```

**To get your dashboard ID:**
1. **Publish** your dashboard (if not already published)
2. Open dashboard in Databricks
3. Click **Share → Embed**
4. Copy the iframe URL
5. Extract ID from URL: `https://HOST/embed/dashboardsv3/{DASHBOARD_ID}?o={ORG_ID}`

**Example:**
```
URL: https://e2-demo-field-eng.cloud.databricks.com/embed/dashboardsv3/01f097746d9d1bbbbc0d7939c55bb781?o=1444828305810485

DASHBOARD_ID: 01f097746d9d1bbbbc0d7939c55bb781
DATABRICKS_ORG_ID: 1444828305810485
```

### 2. **Change Catalog/Schema**

Edit `app.yaml`:

```yaml
- name: CATALOG
  value: "your_catalog_name"
- name: ADMIN_SCHEMA
  value: "your_admin_schema"
```

### 3. **Change SQL Warehouse**

Edit `app.yaml`:

```yaml
- name: SQL_WAREHOUSE_ID
  value: "your-warehouse-id"
```

**To get your warehouse ID:**
1. Go to **SQL Warehouses** in Databricks
2. Click on your warehouse
3. Copy the ID from the URL or **Connection Details**
4. Use only the ID portion (e.g., `862f1d757f0424f7`)

### 4. **Deploy Changes**

After editing `app.yaml`:

```bash
cd /Users/steven.tan/Desktop/lakehouse_monitoring/dq_app
databricks apps deploy steven-dq-app-donotdelete \
  --source-code-path /Workspace/Users/steven.tan@databricks.com/lakehouse_monitoring_v0.1/dq_app
```

## 🏗️ Application Structure

```
dq_app/
├── app.yaml                # Main configuration (EDIT THIS)
├── app.py                  # Main application (reads env vars directly)
├── db_utils.py             # Database utilities (reads env vars directly)
├── requirements.txt        # Python dependencies
└── CONFIGURATION.md        # This guide
```

**Note:** Configuration is read directly from environment variables in the code. No separate `config.py` file needed.

## 🔧 Environment Variables Reference

| Variable | Purpose | Defined In | Example |
|----------|---------|------------|---------|
| `CATALOG` | Unity Catalog name | `app.yaml` | `dbdemos_steventan` |
| `ADMIN_SCHEMA` | Metadata schema | `app.yaml` | `monitoring_admin` |
| `DATA_SCHEMA` | Data schema | `app.yaml` | `lakehouse_monitoring` |
| `OUT_SCHEMA` | Results schema | `app.yaml` | `lakehouse_monitoring_demo_results` |
| `SQL_WAREHOUSE_ID` | SQL Warehouse ID | `app.yaml` | `862f1d757f0424f7` |
| `DATABRICKS_ORG_ID` | Org ID (for dashboards) | `app.yaml` | `1444828305810485` |
| `DASHBOARD_ID` | Dashboard ID (published) | `app.yaml` | `01f097746d9d...` |
| `DATABRICKS_HOST` | Workspace URL | **Auto-provided** | `*.cloud.databricks.com` |
| `DATABRICKS_CLIENT_ID` | OAuth client ID | **Auto-provided** | (automatic) |
| `DATABRICKS_CLIENT_SECRET` | OAuth secret | **Auto-provided** | (automatic) |

## 📚 Additional Resources

- [Databricks Apps Documentation](https://docs.databricks.com/dev-tools/databricks-apps/)
- [Environment Variables Reference](https://docs.databricks.com/dev-tools/databricks-apps/system-env)
- [Dash Framework Documentation](https://dash.plotly.com/)

## ❓ Troubleshooting

### Problem: "Dashboard not loading" or "Failed to load dashboard"

**Checklist:**
1. ✅ Is the dashboard **published**? (Unpublished dashboards cannot be embedded)
2. ✅ Is **"Embed dashboards"** set to **"Allow"** in workspace security settings?
3. ✅ Is the `DASHBOARD_ID` correct in `app.yaml`?
4. ✅ Is the `DATABRICKS_ORG_ID` correct in `app.yaml`?

**Steps to fix:**
1. Go to **Settings** → **Workspace admin** → **Security**
2. Under **External access**, set **Embed dashboards** to **"Allow"**
3. **Publish** your dashboard (if not already published)
4. Get the correct Dashboard ID from **Share → Embed**
5. Update `app.yaml` and redeploy

### Problem: "Authentication failed"
**Solution**: The app uses OAuth automatically. No tokens needed. Ensure the app has proper permissions.

### Problem: "Cannot connect to SQL Warehouse"
**Solution**: Check that `SQL_WAREHOUSE_ID` in `app.yaml` is correct and the app has `CAN_USE` permission.

---

**Last Updated**: October 25, 2025

