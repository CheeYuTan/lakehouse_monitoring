"""
Configuration for DQ Self-Service Portal

This file reads configuration from environment variables defined in databricks.yml.
DO NOT modify this file directly. Edit databricks.yml instead.

Auto-Provided by Databricks Apps (do not define):
- DATABRICKS_HOST: Workspace URL
- DATABRICKS_WORKSPACE_ID: Unique workspace ID  
- DATABRICKS_CLIENT_ID: Service principal client ID
- DATABRICKS_CLIENT_SECRET: OAuth secret for service principal

Reference: https://docs.databricks.com/dev-tools/databricks-apps/system-env
"""
import os

# ========== AUTO-PROVIDED BY DATABRICKS APPS ==========
# These are automatically available, no need to define in databricks.yml
DATABRICKS_HOST = os.getenv("DATABRICKS_HOST")  # e.g., 'workspace.cloud.databricks.com'
DATABRICKS_WORKSPACE_ID = os.getenv("DATABRICKS_WORKSPACE_ID")
# DATABRICKS_CLIENT_ID and DATABRICKS_CLIENT_SECRET are used automatically by db_utils.py

# ========== APP-SPECIFIC CONFIGURATION ==========
# These MUST be defined in databricks.yml

# Dashboard Configuration
DATABRICKS_ORG_ID = os.getenv("DATABRICKS_ORG_ID", "1444828305810485")
DASHBOARD_ID = os.getenv("DASHBOARD_ID", "01f097746d9d1bbbbc0d7939c55bb781")

# Construct dashboard URL
if DATABRICKS_HOST:
    host = DATABRICKS_HOST.replace("https://", "").replace("http://", "")
    DASHBOARD_URL = os.getenv(
        "DASHBOARD_URL",
        f"https://{host}/embed/dashboardsv3/{DASHBOARD_ID}?o={DATABRICKS_ORG_ID}"
    )
else:
    DASHBOARD_URL = os.getenv("DASHBOARD_URL", "")

# Metadata Tables Configuration
CATALOG = os.getenv("CATALOG", "dbdemos_steventan")
ADMIN_SCHEMA = os.getenv("ADMIN_SCHEMA", "monitoring_admin")
DATA_SCHEMA = os.getenv("DATA_SCHEMA", "lakehouse_monitoring")
OUT_SCHEMA = os.getenv("OUT_SCHEMA", "lakehouse_monitoring_demo_results")

# SQL Warehouse Configuration
SQL_WAREHOUSE_ID = os.getenv("SQL_WAREHOUSE_ID", "862f1d757f0424f7")
SQL_WAREHOUSE_HTTP_PATH = f"/sql/1.0/warehouses/{SQL_WAREHOUSE_ID}"

