"""
Database helper functions for querying metadata tables
"""

import pandas as pd
from databricks import sql
import os

# Configuration
CATALOG = os.getenv("CATALOG", "dbdemos_steventan")
ADMIN_SCHEMA = os.getenv("ADMIN_SCHEMA", "monitoring_admin")
DATA_SCHEMA = os.getenv("DATA_SCHEMA", "lakehouse_monitoring")
OUT_SCHEMA = os.getenv("OUT_SCHEMA", "lakehouse_monitoring_demo_results")


def get_databricks_connection():
    """Create connection to Databricks SQL Warehouse"""
    return sql.connect(
        server_hostname=os.getenv("DATABRICKS_SERVER_HOSTNAME"),
        http_path=os.getenv("DATABRICKS_HTTP_PATH"),
        access_token=os.getenv("DATABRICKS_TOKEN")
    )


def execute_query(query):
    """Execute query and return results as pandas DataFrame"""
    try:
        with get_databricks_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query)
                columns = [desc[0] for desc in cursor.description]
                data = cursor.fetchall()
                return pd.DataFrame(data, columns=columns)
    except Exception as e:
        print(f"Error executing query: {e}")
        return pd.DataFrame()


def get_monitored_tables():
    """Get all monitored tables from monitors_control"""
    query = f"""
    SELECT 
        table_catalog,
        table_schema,
        table_name,
        profile_type,
        timestamp_col,
        granularities,
        schedule_cron,
        schedule_tz,
        enabled,
        output_schema_name,
        assets_dir
    FROM {CATALOG}.{ADMIN_SCHEMA}.monitors_control
    ORDER BY table_schema, table_name
    """
    return execute_query(query)


def get_metric_templates():
    """Get all metric templates"""
    query = f"""
    SELECT 
        template_name,
        description,
        metric_type,
        dimension,
        threshold_direction,
        good_threshold,
        acceptable_threshold,
        input_columns,
        definition_template
    FROM {CATALOG}.{ADMIN_SCHEMA}.metric_templates
    ORDER BY dimension, template_name
    """
    return execute_query(query)


def get_metric_bindings():
    """Get all metric bindings"""
    query = f"""
    SELECT 
        table_catalog,
        table_schema,
        table_name,
        metric_name,
        template_name,
        metric_type,
        params,
        enabled
    FROM {CATALOG}.{ADMIN_SCHEMA}.metric_bindings
    ORDER BY table_schema, table_name, metric_name
    """
    return execute_query(query)


def get_table_metrics_summary():
    """Get summary of tables with their metrics count"""
    query = f"""
    SELECT 
        mc.table_catalog,
        mc.table_schema,
        mc.table_name,
        mc.enabled as monitor_enabled,
        COUNT(mb.metric_name) as total_metrics,
        SUM(CASE WHEN mb.enabled THEN 1 ELSE 0 END) as active_metrics,
        COLLECT_SET(mt.dimension) as dimensions_covered
    FROM {CATALOG}.{ADMIN_SCHEMA}.monitors_control mc
    LEFT JOIN {CATALOG}.{ADMIN_SCHEMA}.metric_bindings mb
        ON mc.table_catalog = mb.table_catalog
        AND mc.table_schema = mb.table_schema
        AND mc.table_name = mb.table_name
    LEFT JOIN {CATALOG}.{ADMIN_SCHEMA}.metric_templates mt
        ON mb.template_name = mt.template_name
    GROUP BY 
        mc.table_catalog,
        mc.table_schema,
        mc.table_name,
        mc.enabled
    ORDER BY mc.table_schema, mc.table_name
    """
    return execute_query(query)


def get_metrics_by_dimension():
    """Get count of metrics by dimension"""
    query = f"""
    SELECT 
        COALESCE(dimension, 'N/A') as dimension,
        COUNT(DISTINCT template_name) as template_count
    FROM {CATALOG}.{ADMIN_SCHEMA}.metric_templates
    GROUP BY dimension
    ORDER BY template_count DESC
    """
    return execute_query(query)


def get_recent_bindings(limit=5):
    """Get recently added metric bindings (mock with latest data)"""
    query = f"""
    SELECT 
        mb.table_schema,
        mb.table_name,
        mb.metric_name,
        mt.dimension,
        mb.enabled
    FROM {CATALOG}.{ADMIN_SCHEMA}.metric_bindings mb
    LEFT JOIN {CATALOG}.{ADMIN_SCHEMA}.metric_templates mt
        ON mb.template_name = mt.template_name
    ORDER BY mb.table_schema, mb.table_name
    LIMIT {limit}
    """
    return execute_query(query)

