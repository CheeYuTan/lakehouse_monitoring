"""
Configuration for DQ Self-Service Portal
"""
import os

# Databricks Configuration
DATABRICKS_HOST = os.getenv("DATABRICKS_HOST", "e2-demo-field-eng.cloud.databricks.com")
DATABRICKS_ORG_ID = os.getenv("DATABRICKS_ORG_ID", "1444828305810485")

# Dashboard Configuration
DASHBOARD_ID = os.getenv("DASHBOARD_ID", "01f097746d9d1bbbbc0d7939c55bb781")

# Construct dashboard URL
DASHBOARD_URL = os.getenv(
    "DASHBOARD_URL",
    f"https://{DATABRICKS_HOST}/embed/dashboardsv3/{DASHBOARD_ID}?o={DATABRICKS_ORG_ID}"
)

# Metadata Tables Configuration
CATALOG = os.getenv("CATALOG", "dbdemos_steventan")
ADMIN_SCHEMA = os.getenv("ADMIN_SCHEMA", "monitoring_admin")
DATA_SCHEMA = os.getenv("DATA_SCHEMA", "lakehouse_monitoring")
OUT_SCHEMA = os.getenv("OUT_SCHEMA", "lakehouse_monitoring_demo_results")

# SQL Warehouse Configuration
SQL_WAREHOUSE_ID = os.getenv("SQL_WAREHOUSE_ID", "862f1d757f0424f7")
SQL_WAREHOUSE_HTTP_PATH = f"/sql/1.0/warehouses/{SQL_WAREHOUSE_ID}"
DATABRICKS_TOKEN = os.getenv("DATABRICKS_TOKEN", "")

