"""
Database utilities for querying metadata tables
Following Databricks Apps Cookbook best practices:
https://apps-cookbook.dev/docs/dash/tables/tables_read
"""
import pandas as pd
import os
from functools import lru_cache
from databricks import sql
from databricks.sdk.core import Config

cfg = Config()  # Automatically configured in Databricks Apps

# Configuration from environment variables
CATALOG = os.getenv("CATALOG", "dbdemos_steventan")
ADMIN_SCHEMA = os.getenv("ADMIN_SCHEMA", "monitoring_admin")
SQL_WAREHOUSE_ID = os.getenv("SQL_WAREHOUSE_ID", "862f1d757f0424f7")
SQL_WAREHOUSE_HTTP_PATH = f"/sql/1.0/warehouses/{SQL_WAREHOUSE_ID}"

@lru_cache(maxsize=1)
def get_connection(http_path):
    """Get cached SQL connection
    
    Uses Databricks SDK OAuth authentication for Databricks Apps.
    Connection is cached to improve performance.
    """
    print(f"🔌 Creating new SQL connection to: {http_path}")
    return sql.connect(
        server_hostname=cfg.host,
        http_path=http_path,
        credentials_provider=lambda: cfg.authenticate
    )

def execute_query(query):
    """Execute query and return DataFrame"""
    import time
    
    start_time = time.time()
    print(f"\n{'='*60}")
    print(f"🔍 STARTING QUERY EXECUTION")
    print(f"{'='*60}")
    
    try:
        print("⏳ Step 1: Getting SQL connection...")
        print(f"   Server: {cfg.host}")
        print(f"   Warehouse: {SQL_WAREHOUSE_HTTP_PATH}")
        
        connection_start = time.time()
        connection = get_connection(SQL_WAREHOUSE_HTTP_PATH)
        connection_time = time.time() - connection_start
        print(f"✅ Connection ready in {connection_time:.2f}s")
            
        print(f"⏳ Step 2: Executing query...")
        print(f"📝 Query: {query[:200]}...")
        
        query_start = time.time()
        with connection.cursor() as cursor:
            cursor.execute(query)
            query_exec_time = time.time() - query_start
            print(f"✅ Query executed in {query_exec_time:.2f}s")
            
            print(f"⏳ Step 3: Fetching results...")
            fetch_start = time.time()
            result = cursor.fetchall_arrow().to_pandas()
            fetch_time = time.time() - fetch_start
            print(f"✅ Fetched {len(result)} rows in {fetch_time:.2f}s")
            
            total_time = time.time() - start_time
            print(f"\n{'='*60}")
            print(f"✅ QUERY COMPLETE - Total time: {total_time:.2f}s")
            print(f"   - Connection: {connection_time:.2f}s")
            print(f"   - Query execution: {query_exec_time:.2f}s")
            print(f"   - Fetch results: {fetch_time:.2f}s")
            print(f"   - Rows returned: {len(result)}")
            print(f"{'='*60}\n")
            
            return result
                
    except Exception as e:
        total_time = time.time() - start_time
        print(f"\n{'='*60}")
        print(f"❌ QUERY FAILED after {total_time:.2f}s")
        print(f"❌ Error: {e}")
        print(f"📝 Query was: {query[:300]}")
        print(f"{'='*60}\n")
        import traceback
        traceback.print_exc()
        return pd.DataFrame()

def get_monitors_control():
    """Get all monitored tables"""
    query = f"""
    SELECT 
        table_catalog as Catalog,
        table_schema as Schema,
        table_name as `Table`,
        profile_type as `Profile Type`,
        timestamp_col as `Timestamp Column`,
        granularities as Granularities,
        schedule_cron as Schedule,
        enabled as Status
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
        dimension,
        metric_type,
        threshold_direction,
        good_threshold,
        acceptable_threshold
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
        enabled
    FROM {CATALOG}.{ADMIN_SCHEMA}.metric_bindings
    ORDER BY table_schema, table_name, metric_name
    """
    return execute_query(query)

def get_bindings_with_templates():
    """Get bindings joined with template info"""
    query = f"""
    SELECT 
        mb.table_schema,
        mb.table_name,
        mb.metric_name,
        mt.template_name,
        mt.dimension,
        mt.description,
        mb.enabled
    FROM {CATALOG}.{ADMIN_SCHEMA}.metric_bindings mb
    LEFT JOIN {CATALOG}.{ADMIN_SCHEMA}.metric_templates mt
        ON mb.template_name = mt.template_name
    ORDER BY mb.table_schema, mb.table_name, mt.dimension
    """
    return execute_query(query)

def get_all_metric_names_for_table(table_schema, table_name):
    """
    Get ALL metric names for a table (for debugging).
    
    Args:
        table_schema: Schema name
        table_name: Table name
    
    Returns:
        List of all metric names
    """
    query = f"""
    SELECT metric_name
    FROM {CATALOG}.{ADMIN_SCHEMA}.metric_bindings
    WHERE table_schema = '{table_schema}'
      AND table_name = '{table_name}'
    ORDER BY metric_name
    """
    
    print(f"\n🔍 DEBUG: Querying ALL metric names for {table_schema}.{table_name}")
    df = execute_query(query)
    
    if not df.empty:
        metric_names = df['metric_name'].tolist()
        print(f"📋 Found {len(metric_names)} metrics:")
        for name in metric_names:
            print(f"   - {name}")
    else:
        print("   (No metrics found)")
    
    return metric_names if not df.empty else []

def get_function_definition(function_name):
    """Get the SQL definition of a function
    
    Args:
        function_name: Full function name (e.g., schema.function_name or just function_name)
    
    Returns:
        DataFrame with function definition
    """
    # Extract just the function name if schema is included
    if '.' in function_name:
        parts = function_name.split('.')
        schema_name = parts[-2] if len(parts) >= 2 else None
        func_name_only = parts[-1]
    else:
        schema_name = None
        func_name_only = function_name
    
    print(f"      🔍 Querying function: schema={schema_name}, name={func_name_only}")
    
    query = f"""
    SELECT routine_definition, routine_schema, routine_name
    FROM {CATALOG}.information_schema.routines
    WHERE routine_name = '{func_name_only}'
       OR CONCAT(routine_schema, '.', routine_name) = '{function_name}'
    LIMIT 1
    """
    
    result = execute_query(query)
    if not result.empty:
        print(f"         ✅ Found: {result.iloc[0]['routine_schema']}.{result.iloc[0]['routine_name']}")
    else:
        print(f"         ❌ Not found")
    
    return result

def get_function_parameters(function_name):
    """Get the parameters of a function from information_schema
    
    Args:
        function_name: Function name (with or without schema)
    
    Returns:
        List of dicts with parameter info: [{'name': 'param1', 'type': 'STRING'}, ...]
    """
    # Extract just the function name if schema is included
    if '.' in function_name:
        parts = function_name.split('.')
        func_name_only = parts[-1]
    else:
        func_name_only = function_name
    
    query = f"""
    SELECT DISTINCT
        p.parameter_name,
        p.data_type,
        p.ordinal_position
    FROM {CATALOG}.information_schema.parameters p
    JOIN {CATALOG}.information_schema.routines r 
        ON p.specific_name = r.specific_name
    WHERE (r.routine_name = '{func_name_only}'
       OR CONCAT(r.routine_schema, '.', r.routine_name) = '{function_name}')
    ORDER BY p.ordinal_position
    """
    
    try:
        df = execute_query(query)
        if df.empty:
            return []
        return [
            {'name': row['parameter_name'], 'type': row['data_type']} 
            for _, row in df.iterrows()
        ]
    except Exception as e:
        print(f"❌ Error fetching function parameters: {e}")
        return []

def get_custom_metrics_for_table(table_schema, table_name, include_details=False):
    """Get custom metrics for a specific table
    
    Args:
        table_schema: Schema name
        table_name: Table name
        include_details: If False, exclude metrics with 'details' in name (default: False)
    """
    query = f"""
    SELECT 
        mb.metric_name as `Metric Name`,
        mt.template_name as Template,
        mt.description as Description,
        mt.dimension as Dimension,
        mt.definition_template as Definition,
        mt.threshold_direction as threshold_direction,
        mt.good_threshold as good_threshold,
        mt.acceptable_threshold as acceptable_threshold,
        mb.enabled as Status,
        mb.input_columns as `Input Columns`,
        mb.params as `Parameters`
    FROM {CATALOG}.{ADMIN_SCHEMA}.metric_bindings mb
    LEFT JOIN {CATALOG}.{ADMIN_SCHEMA}.metric_templates mt
        ON mb.template_name = mt.template_name
    WHERE mb.table_schema = '{table_schema}'
        AND mb.table_name = '{table_name}'
        {'AND mb.metric_name NOT LIKE "%details%" AND mb.metric_name NOT LIKE "%_json"' if not include_details else ''}
    ORDER BY mt.dimension, mb.metric_name
    """
    return execute_query(query)

def get_detail_metric_for_ratio(table_schema, table_name, ratio_metric_name):
    """Get the detail metric associated with a ratio metric
    
    Supports multiple naming patterns:
      1. missing_value_ratio_customer_id → missing_value_ratio_customer_id_details_json
      2. missing_value_ratio → missing_value_details_json (strip _ratio from template)
    """
    # Try multiple patterns to find the detail metric
    # Pattern 1: Simply append _details_json (for custom named metrics)
    detail_patterns = [
        f"{ratio_metric_name}_details_json",
        # Pattern 2: Replace _ratio with _details_json (for template-based metrics)
        ratio_metric_name.replace('_ratio', '_details_json'),
        ratio_metric_name.replace('_rate', '_details_json'),
        ratio_metric_name.replace('_pct', '_details_json'),
    ]
    
    # Remove duplicates while preserving order
    detail_patterns = list(dict.fromkeys(detail_patterns))
    
    # Build query to check for any of these patterns
    pattern_conditions = " OR ".join([f"mb.metric_name = '{pattern}'" for pattern in detail_patterns])
    
    query = f"""
    SELECT 
        mb.metric_name as `Metric Name`,
        mt.template_name as Template,
        mt.description as Description,
        mt.dimension as Dimension,
        mt.definition_template as Definition,
        mb.enabled as Status,
        mb.input_columns as `Input Columns`,
        mb.params as `Parameters`
    FROM {CATALOG}.{ADMIN_SCHEMA}.metric_bindings mb
    LEFT JOIN {CATALOG}.{ADMIN_SCHEMA}.metric_templates mt
        ON mb.template_name = mt.template_name
    WHERE mb.table_schema = '{table_schema}'
        AND mb.table_name = '{table_name}'
        AND ({pattern_conditions})
    LIMIT 1
    """
    return execute_query(query)

def update_monitor_control(catalog, schema, table, updates):
    """Update a monitor in the monitors_control table
    
    Args:
        catalog: Table catalog (part of composite key)
        schema: Table schema (part of composite key)
        table: Table name (part of composite key)
        updates: Dictionary of column names and new values
    
    Returns:
        bool: True if update successful, False otherwise
    """
    import time
    
    try:
        print(f"\n{'='*60}")
        print(f"🔄 UPDATING MONITOR: {catalog}.{schema}.{table}")
        print(f"{'='*60}")
        
        # Build SET clause from updates
        set_clauses = []
        for col, val in updates.items():
            if col not in ['table_catalog', 'table_schema', 'table_name']:  # Don't update key fields
                if val is None:
                    set_clauses.append(f"{col} = NULL")
                elif isinstance(val, bool):
                    set_clauses.append(f"{col} = {str(val).upper()}")
                elif isinstance(val, (int, float)):
                    set_clauses.append(f"{col} = {val}")
                elif isinstance(val, list):
                    # Handle arrays (like granularities)
                    # Convert Python list to SQL array format: array('val1', 'val2')
                    array_items = ', '.join([f"'{item}'" for item in val])
                    set_clauses.append(f"{col} = array({array_items})")
                else:
                    # Escape single quotes in string values
                    escaped_val = str(val).replace("'", "''")
                    set_clauses.append(f"{col} = '{escaped_val}'")
        
        if not set_clauses:
            print("⚠️  No fields to update")
            return True
        
        set_clause = ", ".join(set_clauses)
        
        query = f"""
        UPDATE {CATALOG}.{ADMIN_SCHEMA}.monitors_control
        SET {set_clause}
        WHERE table_catalog = '{catalog}'
          AND table_schema = '{schema}'
          AND table_name = '{table}'
        """
        
        print(f"📝 Update query: {query}")
        
        start_time = time.time()
        connection = get_connection(SQL_WAREHOUSE_HTTP_PATH)
        
        with connection.cursor() as cursor:
            cursor.execute(query)
            # Commit the transaction
            connection.commit()
            
        elapsed_time = time.time() - start_time
        print(f"✅ UPDATE completed in {elapsed_time:.2f}s")
        print(f"{'='*60}\n")
        
        return True
        
    except Exception as e:
        print(f"❌ UPDATE FAILED: {e}")
        import traceback
        traceback.print_exc()
        print(f"{'='*60}\n")
        return False

def get_dq_functions():
    """
    Get all DQ functions from the monitoring_admin schema.
    Excludes build_dq_all_metrics_view_from_meta.
    
    Returns:
        DataFrame with function details (name, parameters, return_type, comment)
    """
    # Query functions with parameters using information_schema
    query = f"""
    SELECT 
        r.routine_name as function_name,
        r.routine_definition as definition,
        r.data_type as return_type,
        r.comment as function_comment,
        p.parameter_name,
        p.data_type as parameter_type,
        p.comment as parameter_comment,
        p.ordinal_position
    FROM {CATALOG}.information_schema.routines r
    LEFT JOIN {CATALOG}.information_schema.parameters p
        ON r.specific_name = p.specific_name
    WHERE r.routine_schema = '{ADMIN_SCHEMA}'
      AND r.routine_type = 'FUNCTION'
      AND r.routine_name != 'build_dq_all_metrics_view_from_meta'
    ORDER BY r.routine_name, p.ordinal_position
    """
    
    print(f"\n🔍 Fetching DQ functions from {CATALOG}.{ADMIN_SCHEMA}...")
    print(f"📝 Query: {query}")
    return execute_query(query)

def parse_function_metadata(function_comment):
    """
    Parse structured metadata from function COMMENT field.
    
    Returns dict with: description, usage, related_function
    """
    import re
    
    if not function_comment:
        return {}
    
    metadata = {}
    
    # Extract description (first line or before "Returns:")
    desc_match = re.search(r'^(.*?)(?:Returns:|Usage:|Related:)', function_comment, re.DOTALL)
    if desc_match:
        metadata['description'] = desc_match.group(1).strip()
    
    # Extract usage example
    usage_match = re.search(r'Usage:\s*(.+?)(?:\n|Related:|$)', function_comment, re.DOTALL)
    if usage_match:
        metadata['usage'] = usage_match.group(1).strip()
    
    # Extract related function
    related_match = re.search(r'Related:\s*(\w+)', function_comment)
    if related_match:
        metadata['related_function'] = related_match.group(1).strip()
    
    # Extract return description
    returns_match = re.search(r'Returns:\s*(.+?)(?:\n|Usage:|Related:|$)', function_comment, re.DOTALL)
    if returns_match:
        metadata['returns'] = returns_match.group(1).strip()
    
    return metadata

def get_dq_functions_structured():
    """
    Get DQ functions organized by type (ratio vs detail) with parsed metadata.
    
    Returns:
        dict with 'ratio_functions' and 'detail_functions' lists
    """
    import pandas as pd
    import re
    
    df = get_dq_functions()
    
    if df.empty:
        return {'ratio_functions': [], 'detail_functions': []}
    
    # Group by function to consolidate parameters
    functions = []
    for func_name in df['function_name'].unique():
        func_rows = df[df['function_name'] == func_name]
        first_row = func_rows.iloc[0]
        
        # Get parameters
        params = []
        for _, param_row in func_rows.iterrows():
            if pd.notna(param_row.get('parameter_name')):
                params.append({
                    'name': param_row['parameter_name'],
                    'type': param_row.get('parameter_type', 'STRING'),
                    'comment': param_row.get('parameter_comment', '')
                })
        
        # Parse metadata from comment
        metadata = parse_function_metadata(first_row.get('function_comment', ''))
        
        # Determine category based on name pattern
        is_ratio = bool(re.search(r'(_ratio|_rate|_pct)(_bit)?$', func_name.lower()))
        
        functions.append({
            'name': func_name,
            'type': 'ratio' if is_ratio else 'detail',
            'return_type': first_row['return_type'],
            'definition': first_row.get('definition', ''),
            'parameters': params,
            'description': metadata.get('description', ''),
            'usage': metadata.get('usage', ''),
            'related_function': metadata.get('related_function', ''),
            'returns': metadata.get('returns', '')
        })
    
    # Separate into ratio and detail functions
    ratio_functions = [f for f in functions if f['type'] == 'ratio']
    detail_functions = [f for f in functions if f['type'] == 'detail']
    
    return {
        'ratio_functions': ratio_functions,
        'detail_functions': detail_functions
    }

def save_custom_metric(schema, table, metric_name, function_name, input_columns, good_threshold, acceptable_threshold, enabled):
    """
    Save a new custom metric binding to the metric_bindings table.
    
    Args:
        schema: Table schema
        table: Table name
        metric_name: Name of the metric
        function_name: DQ function name
        input_columns: Dict of parameter names to column names (will be stored in params)
        good_threshold: Good threshold value
        acceptable_threshold: Acceptable threshold value
        enabled: Boolean, is metric enabled
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        print(f"\n💾 Saving custom metric: {metric_name}")
        
        # Build params map from input_columns dict
        # Format: map('PARAM1', 'column1', 'PARAM2', 'column2', ...)
        params_items = []
        for param_name, column_name in input_columns.items():
            params_items.append(f"'{param_name}'")
            params_items.append(f"'{column_name}'")
        
        params_str = ', '.join(params_items) if params_items else ''
        params_map = f"map({params_str})" if params_str else "map()"
        
        # Build threshold values (NULL for detail metrics)
        good_threshold_str = 'NULL' if good_threshold is None else str(good_threshold)
        acceptable_threshold_str = 'NULL' if acceptable_threshold is None else str(acceptable_threshold)
        
        # Determine output_spark_type based on template name
        # Detail metrics (containing 'details' or '_json') should be string
        is_detail = 'details' in function_name.lower() or '_json' in function_name.lower()
        output_type = 'string' if is_detail else 'double'
        
        # Insert into metric_bindings table
        # Always use array(':table') for input_columns, actual columns go in params
        bindings_query = f"""
        INSERT INTO {CATALOG}.{ADMIN_SCHEMA}.metric_bindings
        (table_catalog, table_schema, table_name, metric_name, template_name, 
         metric_type, output_spark_type, input_columns, params, enabled)
        VALUES (
            '{CATALOG}',
            '{schema}',
            '{table}',
            '{metric_name}',
            '{function_name}',
            'AGGREGATE',
            '{output_type}',
            array(':table'),
            {params_map},
            {str(enabled).upper()}
        )
        """
        
        print(f"📝 Insert bindings query: {bindings_query}")
        
        connection = get_connection(SQL_WAREHOUSE_HTTP_PATH)
        cursor = connection.cursor()
        cursor.execute(bindings_query)
        connection.commit()
        
        print(f"✅ Custom metric saved successfully")
        return True
        
    except Exception as e:
        print(f"❌ Error saving custom metric: {e}")
        import traceback
        traceback.print_exc()
        return False


def delete_custom_metric(table_schema, table_name, metric_name):
    """Delete a custom metric from the database
    
    This will delete both the ratio metric and any associated detail metrics.
    
    Args:
        table_schema: Schema of the table
        table_name: Name of the table
        metric_name: Name of the metric to delete (ratio metric)
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        print(f"\n🗑️ Deleting custom metric: {metric_name}")
        
        connection = get_connection(SQL_WAREHOUSE_HTTP_PATH)
        cursor = connection.cursor()
        
        # First, find any associated detail metrics
        detail_metric_df = get_detail_metric_for_ratio(table_schema, table_name, metric_name)
        detail_metric_name = None
        
        print(f"   Detail metric query returned: {len(detail_metric_df)} row(s)")
        if not detail_metric_df.empty:
            print(f"   Detail metric DataFrame columns: {detail_metric_df.columns.tolist()}")
            print(f"   Detail metric DataFrame values: {detail_metric_df.iloc[0].to_dict()}")
            detail_metric_name = detail_metric_df.iloc[0]['Metric Name']
            print(f"   ✅ Found associated detail metric: '{detail_metric_name}'")
        
        # Delete the ratio metric
        delete_ratio_query = f"""
        DELETE FROM {CATALOG}.{ADMIN_SCHEMA}.metric_bindings
        WHERE table_schema = '{table_schema}'
          AND table_name = '{table_name}'
          AND metric_name = '{metric_name}'
        """
        
        print(f"📝 Delete ratio query: {delete_ratio_query}")
        cursor.execute(delete_ratio_query)
        rows_affected_ratio = cursor.rowcount
        print(f"   Ratio metric deleted: {rows_affected_ratio} row(s)")
        
        # Delete the detail metric if it exists
        rows_affected_detail = 0
        if detail_metric_name:
            delete_detail_query = f"""
            DELETE FROM {CATALOG}.{ADMIN_SCHEMA}.metric_bindings
            WHERE table_schema = '{table_schema}'
              AND table_name = '{table_name}'
              AND metric_name = '{detail_metric_name}'
            """
            
            print(f"📝 Delete detail query: {delete_detail_query}")
            cursor.execute(delete_detail_query)
            rows_affected_detail = cursor.rowcount
            print(f"   Detail metric deleted: {rows_affected_detail} row(s)")
        
        connection.commit()
        
        # Note: Some database drivers return -1 for rowcount on DELETE
        # So we verify deletion by checking if the metric still exists
        verify_query = f"""
        SELECT COUNT(*) as count
        FROM {CATALOG}.{ADMIN_SCHEMA}.metric_bindings
        WHERE table_schema = '{table_schema}'
          AND table_name = '{table_name}'
          AND metric_name = '{metric_name}'
        """
        
        cursor.execute(verify_query)
        result = cursor.fetchone()
        metric_still_exists = result[0] > 0 if result else True
        
        if not metric_still_exists:
            total_deleted = (1 if rows_affected_ratio != 0 else 0) + (1 if detail_metric_name and rows_affected_detail != 0 else 0)
            print(f"✅ Custom metric '{metric_name}' deleted successfully (estimated {total_deleted} metrics)")
            return True
        else:
            print(f"⚠️ Metric '{metric_name}' still exists after deletion attempt")
            return False
        
    except Exception as e:
        print(f"❌ Error deleting custom metric: {e}")
        import traceback
        traceback.print_exc()
        return False

