# Configuration Guide

This app is deployed as a **Databricks App** and uses Databricks-native configuration.

## 📋 Configuration Files

### ✅ **`databricks.yml`** (Main Configuration)

This is the **only configuration file** you need to modify. It defines:

```yaml
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

### ✅ **`config.py`** (Read-Only)

This file reads environment variables from `databricks.yml`. **Do not modify directly.**

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

Edit `databricks.yml`:

```yaml
- name: DASHBOARD_ID
  value: "your-new-dashboard-id"
```

To get your dashboard ID:
1. Open dashboard in Databricks
2. Click **Share → Embed**
3. Extract ID from URL: `https://HOST/embed/dashboardsv3/{DASHBOARD_ID}?o={ORG_ID}`

### 2. **Change Catalog/Schema**

Edit `databricks.yml`:

```yaml
- name: CATALOG
  value: "your_catalog_name"
- name: ADMIN_SCHEMA
  value: "your_admin_schema"
```

### 3. **Change SQL Warehouse**

Edit `databricks.yml`:

```yaml
- name: SQL_WAREHOUSE_ID
  value: "your-warehouse-id"
```

To get your warehouse ID:
1. Go to **SQL Warehouses** in Databricks
2. Click on your warehouse
3. Copy the ID from the URL or **Connection Details**

### 4. **Deploy Changes**

After editing `databricks.yml`:

```bash
cd /Users/steven.tan/Desktop/lakehouse_monitoring/dq_app
databricks apps deploy steven-dq-app-donotdelete \
  --profile e2-demo-field-eng \
  --source-code-path /Workspace/Users/steven.tan@databricks.com/lakehouse_monitoring_v0.1/dq_app
```

## 🏗️ Application Structure

```
dq_app/
├── databricks.yml          # Main configuration (EDIT THIS)
├── config.py               # Config reader (read-only)
├── app.py                  # Main application
├── db_utils.py             # Database utilities
├── requirements.txt        # Python dependencies
└── README.md               # General documentation
```

## 🔧 Environment Variables Reference

| Variable | Purpose | Defined In | Example |
|----------|---------|------------|---------|
| `CATALOG` | Unity Catalog name | `databricks.yml` | `dbdemos_steventan` |
| `ADMIN_SCHEMA` | Metadata schema | `databricks.yml` | `monitoring_admin` |
| `DATA_SCHEMA` | Data schema | `databricks.yml` | `lakehouse_monitoring` |
| `OUT_SCHEMA` | Results schema | `databricks.yml` | `lakehouse_monitoring_demo_results` |
| `SQL_WAREHOUSE_ID` | SQL Warehouse ID | `databricks.yml` | `862f1d757f0424f7` |
| `DATABRICKS_ORG_ID` | Org ID (for dashboards) | `databricks.yml` | `1444828305810485` |
| `DASHBOARD_ID` | Dashboard ID | `databricks.yml` | `01f097746d9d...` |
| `DATABRICKS_HOST` | Workspace URL | **Auto-provided** | `*.cloud.databricks.com` |
| `DATABRICKS_CLIENT_ID` | OAuth client ID | **Auto-provided** | (automatic) |
| `DATABRICKS_CLIENT_SECRET` | OAuth secret | **Auto-provided** | (automatic) |

## 📚 Additional Resources

- [Databricks Apps Documentation](https://docs.databricks.com/dev-tools/databricks-apps/)
- [Environment Variables Reference](https://docs.databricks.com/dev-tools/databricks-apps/system-env)
- [Dash Framework Documentation](https://dash.plotly.com/)

## ❓ Troubleshooting

### Problem: "Authentication failed"
**Solution**: The app uses OAuth automatically. No tokens needed. Ensure the app has proper permissions.

### Problem: "Cannot connect to SQL Warehouse"
**Solution**: Check that `SQL_WAREHOUSE_ID` in `databricks.yml` is correct and the app has `CAN_USE` permission.

### Problem: "Dashboard not loading"
**Solution**: Verify `DASHBOARD_ID` and `DATABRICKS_ORG_ID` are correct. Check dashboard sharing settings.

---

**Last Updated**: October 25, 2025

