"""
Data Quality Self-Service Portal - Main Application
"""
import os
import pandas as pd
from dash import Dash, dcc, html, callback, Input, Output, State, dash_table, ALL, ctx, no_update
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
import db_utils

# ========== CONFIGURATION ==========
# Read from environment variables defined in app.yaml

# Auto-provided by Databricks Apps
DATABRICKS_HOST = os.getenv("DATABRICKS_HOST")

# App-specific configuration (defined in app.yaml)
CATALOG = os.getenv("CATALOG", "dbdemos_steventan")
ADMIN_SCHEMA = os.getenv("ADMIN_SCHEMA", "monitoring_admin")
DATA_SCHEMA = os.getenv("DATA_SCHEMA", "lakehouse_monitoring")
OUT_SCHEMA = os.getenv("OUT_SCHEMA", "lakehouse_monitoring_demo_results")
SQL_WAREHOUSE_ID = os.getenv("SQL_WAREHOUSE_ID", "862f1d757f0424f7")
SQL_WAREHOUSE_HTTP_PATH = f"/sql/1.0/warehouses/{SQL_WAREHOUSE_ID}"
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

# Initialize the Dash app with Bootstrap styling
dash_app = Dash(
    __name__, 
    external_stylesheets=[dbc.themes.BOOTSTRAP, dbc.icons.FONT_AWESOME],
    suppress_callback_exceptions=True,  # Allow callbacks for dynamically created components
    update_title=None  # Disable clientside callbacks caching
)
dash_app.title = "DQ Self-Service Portal v2.0"

# Navigation bar
navbar = dbc.Navbar(
    dbc.Container([
        html.A(
            dbc.Row([
                dbc.Col(html.I(className="fas fa-shield-alt", style={"fontSize": "24px"})),
                dbc.Col(dbc.NavbarBrand("Data Quality Self-Service Portal", className="ms-2")),
            ],
            align="center",
            className="g-0",
            ),
            href="/",
            style={"textDecoration": "none"},
        ),
        dbc.NavbarToggler(id="navbar-toggler"),
        dbc.Collapse(
            dbc.Nav([
                dbc.NavItem(dbc.NavLink("Dashboard", href="/", active="exact", external_link=False)),
                dbc.NavItem(dbc.NavLink("Configuration", href="/config", active="exact", external_link=False)),
                dbc.NavItem(dbc.NavLink("Function Catalog", href="/functions", active="exact", external_link=False)),
            ],
            className="ms-auto",
            navbar=True,
            ),
            id="navbar-collapse",
            navbar=True,
        ),
    ],
    fluid=True,
    ),
    color="dark",
    dark=True,
    className="mb-4",
)

# App layout with routing
dash_app.layout = html.Div([
    dcc.Location(id='url', refresh=True),  # Enable refresh for full page reloads
    navbar,
    # Wrap page content with loading spinner
    dcc.Loading(
        id="loading-page",
        type="default",
        children=dbc.Container(id='page-content', fluid=True),
        fullscreen=True,  # Show loading overlay over the entire page
        style={'backgroundColor': 'rgba(255, 255, 255, 0.8)'}  # Semi-transparent white background
    ),
    # Toast notification for success messages
    html.Div(id='toast-container', style={
        'position': 'fixed',
        'top': '80px',
        'right': '20px',
        'zIndex': '9999'
    })
])

# Page layouts
def dashboard_layout():
    return dbc.Container([
        dbc.Row([
            dbc.Col([
                html.H2([html.I(className='fas fa-chart-bar me-3'), 'Data Quality Dashboard']),
                html.P('Real-time data quality metrics and trends', className='text-muted')
            ])
        ], className='mb-3'),
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.Iframe(
                            src=DASHBOARD_URL,
                            style={
                                'width': '100%',
                                'height': '800px',
                                'border': 'none'
                            }
                        )
                    ], style={'padding': '0'})
                ], className='shadow')
            ])
        ])
    ], fluid=True)

def format_quality_thresholds(row):
    """Format quality thresholds in a user-friendly way as percentages"""
    direction = row.get('threshold_direction', '')
    good = row.get('good_threshold', '')
    acceptable = row.get('acceptable_threshold', '')
    
    if not direction:
        return ''
    
    # Convert decimal values to percentages
    def to_percentage(value):
        if value == '' or value is None or value == 'N/A':
            return 'N/A'
        try:
            # Convert to float and multiply by 100, then format as percentage
            return f"{float(value) * 100:.1f}%"
        except (ValueError, TypeError):
            return str(value)
    
    good_pct = to_percentage(good)
    acceptable_pct = to_percentage(acceptable)
    
    if direction == 'LOWER_IS_BETTER':
        return f"✅ Good < {good_pct}\n⚠️ Acceptable < {acceptable_pct}\n❌ Bad ≥ {acceptable_pct}"
    elif direction == 'HIGHER_IS_BETTER':
        return f"✅ Good > {good_pct}\n⚠️ Acceptable > {acceptable_pct}\n❌ Bad ≤ {acceptable_pct}"
    else:
        return f"✅ Good: {good_pct}\n⚠️ Acceptable: {acceptable_pct}"

def extract_function_name(definition):
    """Extract the function name from a SQL definition template
    
    Example: 'avg(schema.rule_name(...))' -> 'rule_name'
    """
    import re
    if not definition or definition == 'N/A':
        return None
    
    # Match pattern like: schema.function_name( or just function_name(
    match = re.search(r'[\w]+\.([\w]+)\s*\(', definition)
    if match:
        return match.group(1)
    
    # Fallback: try to match just function_name(
    match = re.search(r'([\w]+)\s*\(', definition)
    if match:
        return match.group(1)
    
    return None

def substitute_parameters(definition, params):
    """Substitute {{PARAM}} placeholders with actual values from params dict or list of tuples"""
    if not definition or definition == 'N/A':
        return definition
    
    # Handle different parameter formats from the database
    params_dict = {}
    if isinstance(params, dict):
        params_dict = params
    elif isinstance(params, list):
        # Convert list of tuples to dict: [('KEY', 'value')] -> {'KEY': 'value'}
        params_dict = {k: v for k, v in params}
    else:
        return definition
    
    result = definition
    for key, value in params_dict.items():
        placeholder = f"{{{{{key}}}}}"
        result = result.replace(placeholder, value)
    
    return result

def substitute_function_params(func_definition, function_params, bound_params):
    """
    Replace function parameter names with actual bound column names in SQL
    
    Args:
        func_definition: The SQL function body (e.g., "CASE WHEN val IS NULL...")
        function_params: List of function parameters with name and type (e.g., [{'name': 'val', 'type': 'STRING'}])
        bound_params: Dict/list mapping placeholder names to column names (e.g., {'VAL_COL': 'customer_id'})
    
    Returns:
        SQL with substituted column names
    """
    if not func_definition or not function_params or not bound_params:
        return func_definition
    
    # Convert bound_params to dict if it's a list
    params_dict = {}
    if isinstance(bound_params, dict):
        params_dict = bound_params
    elif isinstance(bound_params, list):
        params_dict = {k: v for k, v in bound_params}
    else:
        return func_definition
    
    result = func_definition
    bound_values = list(params_dict.values())
    
    # Replace each function parameter with its corresponding bound column value
    # Match by index: first function param gets first bound value, etc.
    import re
    for i, param in enumerate(function_params):
        param_name = param['name']
        if i < len(bound_values):
            column_name = bound_values[i]
            # Replace all occurrences of the parameter name with the column name
            # Use word boundaries to avoid partial replacements
            result = re.sub(r'\b' + re.escape(param_name) + r'\b', column_name, result)
    
    return result

def prepare_dataframe_for_table(df, table_type='monitors'):
    """Convert array/list columns to strings and format for better display"""
    if df.empty:
        return df
    
    df_copy = df.copy()
    
    # Format quality thresholds for custom metrics
    if 'threshold_direction' in df_copy.columns:
        df_copy['Quality Thresholds'] = df_copy.apply(format_quality_thresholds, axis=1)
        # Drop the raw threshold columns
        df_copy = df_copy.drop(['threshold_direction', 'good_threshold', 'acceptable_threshold'], axis=1)
    
    # Convert array columns to strings
    for col in df_copy.columns:
        if col == 'Status' or col == 'enabled':
            # Convert enabled to ✓ or ✗ for better display
            df_copy[col] = df_copy[col].apply(lambda x: '✓ Enabled' if x else '✗ Disabled')
        elif col == 'Granularities' or col == 'granularities':
            # Format granularities nicely
            df_copy[col] = df_copy[col].apply(
                lambda x: ', '.join(x) if isinstance(x, (list, tuple, set)) else str(x)
            )
        elif col in ['Input Columns', 'input_columns']:
            # Format input columns nicely
            df_copy[col] = df_copy[col].apply(
                lambda x: ', '.join(x) if isinstance(x, (list, tuple, set)) else str(x)
            )
        else:
            # Convert other array/list columns to strings
            df_copy[col] = df_copy[col].apply(
                lambda x: ', '.join(map(str, x)) if isinstance(x, (list, tuple, set)) else (str(x) if x is not None else '')
            )
    
    # Reorder columns to put 'Status' last if it exists
    if 'Status' in df_copy.columns:
        cols = [c for c in df_copy.columns if c != 'Status'] + ['Status']
        df_copy = df_copy[cols]
    elif 'enabled' in df_copy.columns:
        cols = [c for c in df_copy.columns if c != 'enabled'] + ['enabled']
        df_copy = df_copy[cols]
    
    return df_copy

def config_layout():
    import time
    
    print("\n" + "="*80)
    print("🚀 LOADING CONFIGURATION PAGE - REAL DATA")
    print("="*80)
    
    page_start = time.time()
    
    # Fetch REAL data from metadata tables
    try:
        print("\n📊 Query: Fetching monitors_control...")
        monitors_start = time.time()
        df_monitors = db_utils.get_monitors_control()
        df_monitors = prepare_dataframe_for_table(df_monitors, 'monitors')
        monitors_time = time.time() - monitors_start
        print(f"✅ Monitors query completed in {monitors_time:.2f}s - {len(df_monitors)} rows")
        
        page_time = time.time() - page_start
        print("\n" + "="*80)
        print(f"✅ PAGE LOADED - Total time: {page_time:.2f}s")
        print("="*80 + "\n")
        
    except Exception as e:
        print(f"\n❌ ERROR LOADING CONFIG DATA: {e}")
        import traceback
        traceback.print_exc()
        # Return error page instead of continuing
        return dbc.Container([
            dbc.Alert([
                html.H4("❌ Error Loading Configuration", className="alert-heading"),
                html.P(f"Failed to load configuration data: {str(e)}"),
                html.Hr(),
                html.P("Please check the application logs for more details.", className="mb-0"),
                dbc.Button("Return to Dashboard", href="/", color="primary", className="mt-3")
            ], color="danger")
        ], fluid=True)
    
    # Create empty DataFrame if query returned no data
    if df_monitors.empty:
        print("⚠️  No data returned from monitors_control query")
        df_monitors = pd.DataFrame(columns=['Catalog', 'Schema', 'Table', 'Profile Type', 'Timestamp Column', 'Granularities', 'Schedule', 'Status'])
    
    return dbc.Container([
        dbc.Row([
            dbc.Col([
                html.H2([html.I(className='fas fa-cog me-3'), 'Data Quality Configuration']),
                html.P('View and manage your monitoring configuration. Click a table row to view its custom metrics.', className='text-muted')
            ])
        ], className='mb-3'),
        
        # Main Configuration Section
        dbc.Card([
            dbc.CardBody([
                html.H4('📊 Monitored Tables', className='mb-3'),
                html.P(f'Total tables being monitored: {len(df_monitors)}'),
                dbc.Button([html.I(className='fas fa-plus me-2'), 'Register New Table'], 
                          id='register-new-table-btn',
                          color='success', className='mb-3'),
                html.Hr(),
                dash_table.DataTable(
                    id='monitors-table',
                    data=df_monitors.to_dict('records') if not df_monitors.empty else [],
                    columns=[{"name": i, "id": i} for i in df_monitors.columns] if not df_monitors.empty else [],
                    style_table={'overflowX': 'auto'},
                    style_cell={
                        'textAlign': 'left', 
                        'padding': '12px',
                        'fontSize': '14px',
                        'fontFamily': 'system-ui, -apple-system, sans-serif'
                    },
                    style_header={
                        'backgroundColor': '#2272b4',
                        'color': 'white',
                        'fontWeight': 'bold',
                        'textAlign': 'left',
                        'padding': '12px'
                    },
                    style_data_conditional=[
                        # Zebra striping
                        {'if': {'row_index': 'odd'}, 'backgroundColor': '#f8f9fa'},
                        # Selected row highlight
                        {'if': {'state': 'selected'}, 'backgroundColor': '#c8e6ff', 'border': '2px solid #0066cc'},
                        # Status column styling
                        {
                            'if': {
                                'filter_query': '{Status} contains "Enabled"',
                                'column_id': 'Status'
                            },
                            'backgroundColor': '#d4edda',
                            'color': '#155724',
                            'fontWeight': 'bold'
                        },
                        {
                            'if': {
                                'filter_query': '{Status} contains "Disabled"',
                                'column_id': 'Status'
                            },
                            'backgroundColor': '#f8d7da',
                            'color': '#721c24',
                            'fontWeight': 'bold'
                        },
                        # Highlight table name
                        {
                            'if': {'column_id': 'Table'},
                            'fontWeight': '600',
                            'color': '#0066cc'
                        },
                    ],
                    page_size=10,
                    sort_action='native',
                    filter_action='native',
                    row_selectable='single',
                    selected_rows=[],
                    style_cell_conditional=[
                        {'if': {'column_id': 'Catalog'}, 'width': '150px'},
                        {'if': {'column_id': 'Schema'}, 'width': '180px'},
                        {'if': {'column_id': 'Table'}, 'width': '150px'},
                        {'if': {'column_id': 'Status'}, 'width': '120px', 'textAlign': 'center'},
                    ]
                ) if not df_monitors.empty else dbc.Alert('No monitored tables found. Click "Register New Table" to add one.', color='info'),
                
                # Edit button for selected row
                html.Div([
                    dbc.Button([html.I(className='fas fa-edit me-2'), 'Edit Selected'], 
                              id='edit-monitor-btn',
                              color='primary', 
                              className='mt-3',
                              disabled=True)
                ], id='edit-button-container'),
                
                # Custom Metrics Section (expandable) with loading spinner
                dcc.Loading(
                    id="loading-custom-metrics",
                    type="default",
                    children=html.Div(id='custom-metrics-section', className='mt-4')
                ),
                
                # Register New Table Modal
                dbc.Modal([
                    dbc.ModalHeader(dbc.ModalTitle([
                        html.I(className='fas fa-plus-circle me-2'),
                        'Register New Table for Monitoring'
                    ])),
                    dbc.ModalBody([
                        html.Div(id='register-table-form-content'),
                        html.Div(id='register-table-status', className='mt-3')
                    ]),
                    dbc.ModalFooter([
                        dbc.Button("Cancel", id="register-table-cancel", color="secondary", className="me-2"),
                        dbc.Button([
                            html.I(className='fas fa-save me-2'),
                            "Register Table"
                        ], id="register-table-save", color="success"),
                    ]),
                ], id='register-table-modal', size='xl', is_open=False, scrollable=True),
            ])
        ], className='shadow-sm')
    ], fluid=True)

# Callback to show custom metrics when a table is selected
@callback(
    Output('custom-metrics-section', 'children'),
    Input('monitors-table', 'selected_rows'),
    State('monitors-table', 'data')
)
def display_custom_metrics(selected_rows, table_data):
    if not selected_rows or not table_data:
        return html.Div()
    
    # Get selected table info
    selected_idx = selected_rows[0]
    selected_table = table_data[selected_idx]
    # Handle both old and new column names
    table_schema = selected_table.get('Schema', selected_table.get('table_schema'))
    table_name = selected_table.get('Table', selected_table.get('table_name'))
    
    print(f"\n🔍 Fetching custom metrics for {table_schema}.{table_name}...")
    
    try:
        # Fetch custom metrics for this table (exclude details metrics by default)
        df_metrics = db_utils.get_custom_metrics_for_table(table_schema, table_name, include_details=False)
        
        # Keep raw copy before formatting
        df_metrics_raw = df_metrics.copy()
        df_metrics = prepare_dataframe_for_table(df_metrics, 'custom_metrics')
        
        # Count total including details
        df_all = db_utils.get_custom_metrics_for_table(table_schema, table_name, include_details=True)
        total_count = len(df_all)
        details_count = total_count - len(df_metrics)
        
        print(f"✅ Found {len(df_metrics)} main metrics ({details_count} details metrics hidden)")
        
        # Pre-fetch function parameters and definitions for all templates
        function_parameters = {}
        function_definitions = {}
        print(f"\n🔍 Pre-fetching function parameters and definitions...")
        for idx, row in df_metrics_raw.iterrows():
            template_name = row.get('Template', 'N/A')
            definition_template = row.get('Definition', 'N/A')
            
            # Extract actual function name from the SQL definition
            func_name = extract_function_name(definition_template)
            
            if func_name and template_name not in function_parameters:
                print(f"   Template: {template_name}")
                print(f"      Extracted function: {func_name}")
                
                # Fetch function parameters
                params = db_utils.get_function_parameters(func_name)
                if params:
                    function_parameters[template_name] = params
                    print(f"      ✅ Found {len(params)} parameters")
                else:
                    print(f"      ⚠️ No parameters found")
                
                # Fetch function definition
                func_def = db_utils.get_function_definition(func_name)
                if not func_def.empty:
                    function_definitions[template_name] = func_def.iloc[0]['routine_definition']
                    print(f"      ✅ Found function definition")
                else:
                    print(f"      ⚠️ No function definition found")
        print(f"   Total parameter signatures cached: {len(function_parameters)}")
        print(f"   Total definitions cached: {len(function_definitions)}")
        
        # Helper function to substitute parameters in SQL definitions
        def substitute_parameters(definition, params):
            """Substitute {{PARAM}} placeholders in definition with actual values"""
            if not definition or not params:
                return definition or 'N/A'
            
            # Convert params to dict if it's a list of tuples
            if isinstance(params, list):
                params = dict(params)
            elif not isinstance(params, dict):
                params = {}
            
            result = definition
            for key, value in params.items():
                placeholder = f"{{{{{key}}}}}"
                result = result.replace(placeholder, str(value))
            
            return result
        
        # Build metric cards with EXACT same structure as edit page
        metric_cards = []
        for i, (idx, row) in enumerate(df_metrics.iterrows()):
            ratio_name = row['Metric Name']
            ratio_row_raw = df_metrics_raw.iloc[i]
            template_name = row['Template'] if 'Template' in row.index else 'N/A'
            func_definition = function_definitions.get(template_name, None)
            
            # Find associated detail metric (database function handles multiple naming patterns)
            detail_row = db_utils.get_detail_metric_for_ratio(table_schema, table_name, ratio_name)
            
            if not detail_row.empty:
                detail_name = detail_row.iloc[0]['Metric Name']
                print(f"🔍 Ratio: '{ratio_name}' → Detail: '{detail_name}' → Found!")
            else:
                detail_name = ""
                print(f"🔍 Ratio: '{ratio_name}' → No detail metric found")
            
            # EXACT same card structure as edit page
            metric_cards.append(
                dbc.Card([
                    dbc.CardBody([
                        # Main metric info
                        html.Div([
                            html.H6([
                                html.I(className='fas fa-chart-line me-2'),
                                ratio_name
                            ], className='mb-2'),
                            dbc.Row([
                                dbc.Col([
                                    dbc.Badge(row['Dimension'], color='info', className='me-2'),
                                    dbc.Badge(row['Status'], 
                                             color='success' if 'Enabled' in row['Status'] else 'secondary',
                                             className='me-2'),
                                    dbc.Badge([
                                        html.I(className='fas fa-microscope me-1'),
                                        'Detail Capture: ',
                                        html.I(className='fas fa-check-circle') if not detail_row.empty else html.I(className='fas fa-times-circle')
                                    ], 
                                    color='success' if not detail_row.empty else 'secondary',
                                    className='me-2')
                                ], width='auto')
                            ]),
                            # Business-friendly description
                            dbc.Alert([
                                html.Div([
                                    html.I(className='fas fa-info-circle me-2'),
                                    html.Strong("What this checks: ", className='me-1'),
                                    html.Span(row['Description'])
                                ])
                            ], color='light', className='mb-3 py-2 px-3 border'),
                            
                            # Monitored Columns - Display actual bound column values
                            html.Div([
                                html.Div([
                                    html.I(className='fas fa-table me-2', style={'color': '#0d6efd'}),
                                    html.Strong("Monitored Columns", className='mb-2')
                                ], className='mb-2'),
                                (lambda bound_params:
                                    dbc.Table([
                                        html.Thead([
                                            html.Tr([
                                                html.Th("Placeholder", style={'width': '40%', 'backgroundColor': '#f8f9fa'}),
                                                html.Th("Column", style={'width': '60%', 'backgroundColor': '#f8f9fa'})
                                            ])
                                        ]),
                                        html.Tbody([
                                            html.Tr([
                                                html.Td(
                                                    html.Code(param_name, className='px-2 py-1',
                                                            style={'backgroundColor': '#fff3bf', 'color': '#856404', 'borderRadius': '4px'}),
                                                    style={'fontWeight': '500'}
                                                ),
                                                html.Td(
                                                    html.Code(column_value, className='px-2 py-1',
                                                            style={'backgroundColor': '#e7f5ff', 'color': '#1971c2', 'borderRadius': '4px'}),
                                                    style={'fontWeight': '500'}
                                                )
                                            ]) for param_name, column_value in bound_params.items()
                                        ]) if bound_params else html.Tbody([
                                            html.Tr([
                                                html.Td("No parameters bound", colSpan=2, className='text-center text-muted')
                                            ])
                                        ])
                                    ], bordered=True, hover=True, size='sm', className='mb-0')
                                )(
                                    (lambda p: dict(p) if isinstance(p, list) else p if isinstance(p, dict) else {})(ratio_row_raw.get('Parameters', {}))
                                )
                            ], className='mb-3'),
                            
                            # Quality Thresholds - More visual
                            html.Div([
                                html.Div([
                                    html.I(className='fas fa-chart-bar me-2', style={'color': '#37b24d'}),
                                    html.Strong("Quality Thresholds", className='mb-2')
                                ], className='mb-2'),
                                html.Div(row['Quality Thresholds'], className='small ps-3', 
                                         style={'whiteSpace': 'pre-line', 'fontSize': '13px', 'lineHeight': '2'})
                            ], className='mb-3'),
                            
                            # Advanced/Technical Details - Collapsed by default (EXACT same as edit page)
                            html.Details([
                                html.Summary([
                                    html.I(className='fas fa-cog me-2'),
                                    html.Strong("Advanced Technical Details", className='text-muted')
                                ], style={'cursor': 'pointer', 'padding': '8px', 'backgroundColor': '#f8f9fa', 'borderRadius': '4px'}),
                                html.Div([
                                    # Function name
                                    html.Div([
                                        html.Strong("Function Template:", className='small d-block mb-1 text-muted'),
                                        html.Code(template_name, className='small d-block')
                                    ], className='mb-3 mt-3'),
                                    
                                    # SQL Function Call
                                    html.Div([
                                        html.Strong("Generated SQL:", className='small d-block mb-1 text-muted'),
                                        html.Pre(
                                            substitute_parameters(
                                                row.get('Definition', 'N/A') if 'Definition' in row.index else 'N/A',
                                                ratio_row_raw.get('Parameters', {})
                                            ),
                                            className='small bg-white p-2 rounded border',
                                            style={'fontSize': '11px', 'maxHeight': '100px', 'overflow': 'auto', 'fontFamily': 'Monaco, monospace'}
                                        )
                                    ], className='mb-3'),
                                    
                                    # SQL Function Body (with actual column substitution)
                                    html.Div([
                                        html.Strong("Function Implementation (SQL):", className='small d-block mb-1 text-muted'),
                                        html.Pre(
                                            substitute_function_params(
                                                func_definition if func_definition else 'Not available',
                                                function_parameters.get(template_name, []),
                                                ratio_row_raw.get('Parameters', {})
                                            ),
                                            className='small bg-dark text-white p-2 rounded',
                                            style={
                                                'fontSize': '10px',
                                                'maxHeight': '150px',
                                                'overflow': 'auto',
                                                'fontFamily': 'Monaco, Consolas, monospace'
                                            }
                                        )
                                    ]) if func_definition else html.Div()
                                ], className='p-2')
                            ], className='mb-2'),
                        ])
                    ])
                ], className='mb-3')
            )
        
        # Return the card with header and all metric cards
        return dbc.Card([
            dbc.CardHeader([
                html.H5([
                    html.I(className='fas fa-chart-line me-2'),
                    f'Custom Metrics for ',
                    html.Span(f'{table_schema}.{table_name}', className='text-primary fw-bold')
                ], className='mb-0')
            ], className='bg-light'),
            dbc.CardBody([
                html.Div([
                    html.P([
                        f'Showing {len(df_metrics)} custom metrics'
                    ], className='text-muted mb-2'),
                    html.Small('Custom metrics are the key quality checks for this table.', className='text-muted d-block mb-3')
                ]),
                # Display metric cards
                html.Div(metric_cards) if metric_cards else dbc.Alert('No custom metrics configured for this table.', color='info')
            ])
        ], className='border-primary')
        
    except Exception as e:
        print(f"❌ Error fetching custom metrics: {e}")
        import traceback
        traceback.print_exc()
        return dbc.Alert(f'Error loading custom metrics: {str(e)}', color='danger')

# Callback to show detail metric when a ratio metric is selected
@callback(
    Output('detail-metric-section', 'children'),
    Input('custom-metrics-table', 'selected_rows'),
    State('custom-metrics-table', 'data'),
    State('monitors-table', 'selected_rows'),
    State('monitors-table', 'data')
)
def display_detail_metric(selected_metric_rows, metrics_data, selected_table_rows, table_data):
    if not selected_metric_rows or not metrics_data or not selected_table_rows or not table_data:
        return html.Div()
    
    # Get selected metric and table info
    selected_metric = metrics_data[selected_metric_rows[0]]
    metric_name = selected_metric['Metric Name']
    
    # Only show details for ratio metrics
    if '_ratio' not in metric_name:
        return dbc.Alert([
            html.I(className='fas fa-info-circle me-2'),
            'This metric does not have associated detail records. Details are only available for ratio metrics.'
        ], color='info', className='mt-2')
    
    # Get table info
    selected_table = table_data[selected_table_rows[0]]
    table_schema = selected_table.get('Schema', selected_table.get('table_schema'))
    table_name = selected_table.get('Table', selected_table.get('table_name'))
    
    print(f"\n🔍 Fetching detail metric for {metric_name}...")
    
    try:
        # Fetch detail metric
        df_detail = db_utils.get_detail_metric_for_ratio(table_schema, table_name, metric_name)
        df_detail = prepare_dataframe_for_table(df_detail, 'custom_metrics')
        
        if df_detail.empty:
            return dbc.Alert([
                html.I(className='fas fa-exclamation-triangle me-2'),
                f'No detail metric found for {metric_name}'
            ], color='warning', className='mt-2')
        
        print(f"✅ Found detail metric")
        
        return dbc.Card([
            dbc.CardHeader([
                html.H6([
                    html.I(className='fas fa-list-ul me-2'),
                    f'Detail Records for ',
                    html.Span(metric_name, className='text-primary fw-bold')
                ], className='mb-0')
            ], className='bg-light border-start border-5 border-info'),
            dbc.CardBody([
                html.P('This metric provides the detailed records that were aggregated into the ratio above.', 
                       className='text-muted small mb-3'),
                dash_table.DataTable(
                    data=df_detail.to_dict('records'),
                    columns=[{"name": i, "id": i} for i in df_detail.columns],
                    style_table={'overflowX': 'auto'},
                    style_cell={
                        'textAlign': 'left', 
                        'padding': '8px',
                        'fontSize': '12px',
                        'fontFamily': 'system-ui, -apple-system, sans-serif',
                        'whiteSpace': 'normal',
                        'height': 'auto',
                    },
                    style_header={
                        'backgroundColor': '#e9ecef',
                        'color': '#495057',
                        'fontWeight': 'bold',
                        'textAlign': 'left',
                        'padding': '8px',
                        'fontSize': '12px'
                    },
                    style_data_conditional=[
                        {'if': {'row_index': 'odd'}, 'backgroundColor': '#f8f9fa'},
                        # Status column styling
                        {
                            'if': {
                                'filter_query': '{Status} contains "Enabled"',
                                'column_id': 'Status'
                            },
                            'backgroundColor': '#d4edda',
                            'color': '#155724',
                            'fontWeight': 'bold'
                        },
                        {
                            'if': {
                                'filter_query': '{Status} contains "Disabled"',
                                'column_id': 'Status'
                            },
                            'backgroundColor': '#f8d7da',
                            'color': '#721c24',
                            'fontWeight': 'bold'
                        },
                    ],
                    page_size=3,
                    style_cell_conditional=[
                        {'if': {'column_id': 'Metric Name'}, 'width': '220px'},
                        {'if': {'column_id': 'Description'}, 'width': '280px'},
                        {'if': {'column_id': 'Status'}, 'width': '100px', 'textAlign': 'center'},
                    ],
                    tooltip_data=[
                        {
                            column: {'value': str(value), 'type': 'text'}
                            for column, value in row.items()
                        } for row in df_detail.to_dict('records')
                    ],
                    tooltip_duration=None,
                )
            ], className='p-2')
        ], className='border-info mt-2')
        
    except Exception as e:
        print(f"❌ Error fetching detail metric: {e}")
        import traceback
        traceback.print_exc()
        return dbc.Alert(f'Error loading detail metric: {str(e)}', color='danger', className='mt-2')

# Edit page layout
def edit_monitor_layout(catalog, schema, table):
    """Edit page for a specific monitor"""
    import urllib.parse
    
    # Decode URL parameters
    catalog = urllib.parse.unquote(catalog)
    schema = urllib.parse.unquote(schema)
    table = urllib.parse.unquote(table)
    
    try:
        # Fetch the specific monitor data
        query = f"""
        SELECT *
        FROM {CATALOG}.{ADMIN_SCHEMA}.monitors_control
        WHERE table_catalog = '{catalog}'
          AND table_schema = '{schema}'
          AND table_name = '{table}'
        """
        df = db_utils.execute_query(query)
        
        if df.empty:
            return dbc.Container([
                dbc.Alert([
                    html.H4("❌ Monitor Not Found"),
                    html.P(f"No monitor found for {catalog}.{schema}.{table}"),
                    dbc.Button("Back to Configuration", href="/config", color="primary")
                ], color="warning")
            ], fluid=True)
        
        monitor = df.iloc[0].to_dict()
        
        # Fetch table schema to get column names and types
        columns_query = f"""
        DESCRIBE {catalog}.{schema}.{table}
        """
        df_schema = db_utils.execute_query(columns_query)
        
        # Create dropdown options for timestamp column (show all columns with their types)
        timestamp_col_options = [
            {'label': f"{row['col_name']} ({row['data_type']})", 'value': row['col_name']}
            for _, row in df_schema.iterrows()
        ]
        
        # Fetch sample data (10 rows)
        sample_query = f"""
        SELECT * FROM {catalog}.{schema}.{table}
        LIMIT 10
        """
        df_sample = db_utils.execute_query(sample_query)
        
        # Determine initial visibility based on profile type
        profile_type = monitor.get('profile_type', 'TimeSeries')
        print(f"🔍 DEBUG: Loaded profile_type from DB: '{profile_type}' (type: {type(profile_type)})")
        print(f"   Raw monitor data: {monitor}")
        
        # Normalize to handle case variations
        profile_type_normalized = str(profile_type).strip() if profile_type else 'TimeSeries'
        show_timeseries_fields = 'block' if profile_type_normalized == 'TimeSeries' else 'none'
        print(f"   Initial field visibility: {show_timeseries_fields}")
        
        return dbc.Container([
            dbc.Row([
                dbc.Col([
                    html.H2([html.I(className='fas fa-edit me-3'), f'Edit Monitor: {table}']),
                    html.P(f'{catalog}.{schema}.{table}', className='text-muted')
                ])
            ], className='mb-3'),
            
            # Table Preview Section (collapsible)
            dbc.Card([
                dbc.CardHeader(
                    html.Div([
                        html.I(className='fas fa-chevron-down me-2', id='preview-icon'),
                        html.I(className='fas fa-table me-2'),
                        html.Span('Table Preview (10 sample rows)'),
                    ], id='collapse-preview-button', style={'cursor': 'pointer'}),
                    className='bg-light'
                ),
                dbc.Collapse(
                    dbc.CardBody([
                        html.P(f'Sample data from {catalog}.{schema}.{table}', className='text-muted mb-3'),
                        dash_table.DataTable(
                            id='sample-data-table',
                            data=df_sample.to_dict('records') if not df_sample.empty else [],
                            columns=[{"name": i, "id": i} for i in df_sample.columns] if not df_sample.empty else [],
                            style_table={'overflowX': 'auto'},
                            style_cell={
                                'textAlign': 'left',
                                'padding': '10px',
                                'fontSize': '13px',
                                'whiteSpace': 'normal',
                                'height': 'auto',
                            },
                            style_header={
                                'backgroundColor': '#f8f9fa',
                                'fontWeight': 'bold',
                                'textAlign': 'left',
                                'padding': '10px',
                                'borderBottom': '2px solid #dee2e6'
                            },
                            style_data_conditional=[
                                {'if': {'row_index': 'odd'}, 'backgroundColor': '#f8f9fa'},
                            ],
                            page_size=10,
                            tooltip_data=[
                                {
                                    column: {'value': str(value), 'type': 'text'}
                                    for column, value in row.items()
                                } for row in df_sample.to_dict('records')
                            ] if not df_sample.empty else [],
                            tooltip_duration=None,
                        ) if not df_sample.empty else dbc.Alert('No sample data available', color='info')
                    ]),
                    id='collapse-preview',
                    is_open=False  # Collapsed by default
                )
            ], className='shadow mb-4'),
            
            # Important notice about metadata updates
            dbc.Alert([
                html.I(className='fas fa-info-circle me-2'),
                html.Strong("Note: "),
                "Updating this configuration only modifies the metadata. The actual monitoring will be affected when the metadata job is executed next."
            ], color='info', className='mb-4'),
            
            # Edit Form
            dbc.Card([
                dbc.CardBody([
                    dbc.Form([
                        # Profile Type
                        dbc.Row([
                            dbc.Label("Profile Type", width=3),
                            dbc.Col([
                                dbc.Select(
                                    id='edit-profile-type',
                                    options=[
                                        {'label': 'TimeSeries - Monitor data distributions across time windows', 'value': 'TimeSeries'},
                                        {'label': 'Snapshot - Monitor how full table contents change over time', 'value': 'Snapshot'}
                                    ],
                                    value=monitor.get('profile_type', 'TimeSeries')
                                )
                            ], width=9)
                        ], className='mb-3'),
                        
                        # Timestamp Column (shown only for TimeSeries)
                        html.Div([
                            dbc.Row([
                                dbc.Label("Timestamp Column", width=3),
                                dbc.Col([
                                    dbc.Select(
                                        id='edit-timestamp-col',
                                        options=timestamp_col_options,
                                        value=monitor.get('timestamp_col', ''),
                                        placeholder='Select a timestamp column'
                                    ),
                                    dbc.FormText("Required for TimeSeries. Must be TIMESTAMP or convertible to timestamp.")
                                ], width=9)
                            ], className='mb-3')
                        ], id='timestamp-col-section'),
                        
                        # Granularities (shown only for TimeSeries)
                        html.Div([
                            dbc.Row([
                                dbc.Label("Granularities", width=3),
                                dbc.Col([
                                    dbc.Checklist(
                                        id='edit-granularities',
                                        options=[
                                            {'label': '5 minutes', 'value': '5 minutes'},
                                            {'label': '30 minutes', 'value': '30 minutes'},
                                            {'label': '1 hour', 'value': '1 hour'},
                                            {'label': '1 day', 'value': '1 day'},
                                            {'label': '1 week', 'value': '1 week'},
                                            {'label': '1 month', 'value': '1 month'},
                                        ],
                                        value=monitor.get('granularities', []) if monitor.get('granularities') is not None else [],
                                        inline=False
                                    ),
                                    dbc.FormText("Select time windows for metric calculation.")
                                ], width=9)
                            ], className='mb-3')
                        ], id='granularities-section'),
                        
                        # Schedule Builder
                        dbc.Row([
                            dbc.Label("Schedule", width=3),
                            dbc.Col([
                                # Frequency selector
                                html.Div([
                                    html.Span("Every ", className='me-2'),
                                    # Hour interval selector (shown only for hourly)
                                    html.Span(id='hour-interval-section', children=[
                                        dbc.Select(
                                            id='schedule-hour-interval',
                                            options=[
                                                {'label': '1', 'value': '1'},
                                                {'label': '2', 'value': '2'},
                                                {'label': '3', 'value': '3'},
                                                {'label': '4', 'value': '4'},
                                                {'label': '6', 'value': '6'},
                                                {'label': '8', 'value': '8'},
                                                {'label': '12', 'value': '12'},
                                            ],
                                            value='1',
                                            style={'width': '80px', 'display': 'inline-block'}
                                        ),
                                    ], style={'display': 'none'}),
                                    dbc.Select(
                                        id='schedule-frequency',
                                        options=[
                                            {'label': 'Hour', 'value': 'hour'},
                                            {'label': 'Day', 'value': 'day'},
                                            {'label': 'Week', 'value': 'week'},
                                            {'label': 'Month', 'value': 'month'},
                                        ],
                                        value='day',
                                        style={'width': '120px', 'display': 'inline-block'}
                                    ),
                                    # Day of week selector (shown only for weekly)
                                    html.Span(id='day-of-week-section', children=[
                                        html.Span(" on ", className='mx-2'),
                                        dbc.Select(
                                            id='schedule-day-of-week',
                                            options=[
                                                {'label': 'Monday', 'value': 'MON'},
                                                {'label': 'Tuesday', 'value': 'TUE'},
                                                {'label': 'Wednesday', 'value': 'WED'},
                                                {'label': 'Thursday', 'value': 'THU'},
                                                {'label': 'Friday', 'value': 'FRI'},
                                                {'label': 'Saturday', 'value': 'SAT'},
                                                {'label': 'Sunday', 'value': 'SUN'},
                                            ],
                                            value='MON',
                                            style={'width': '150px', 'display': 'inline-block'}
                                        ),
                                    ], style={'display': 'none'}),
                                    # Day of month selector (shown only for monthly)
                                    html.Span(id='day-of-month-section', children=[
                                        html.Span(" on the ", className='mx-2'),
                                        dbc.Select(
                                            id='schedule-day-of-month',
                                            options=[{'label': str(i), 'value': str(i)} for i in range(1, 32)],
                                            value='1',
                                            style={'width': '80px', 'display': 'inline-block'}
                                        ),
                                    ], style={'display': 'none'}),
                                    # Time selector (shown for day/week/month, minute only for hour)
                                    html.Span(id='time-section', children=[
                                        html.Span(" at ", className='mx-2'),
                                        dbc.Select(
                                            id='schedule-hour',
                                            options=[{'label': f'{i:02d}', 'value': str(i)} for i in range(24)],
                                            value='0',
                                            style={'width': '70px', 'display': 'inline-block'}
                                        ),
                                        html.Span(" : ", className='mx-1'),
                                        dbc.Select(
                                            id='schedule-minute',
                                            options=[{'label': f'{i:02d}', 'value': str(i)} for i in range(60)],
                                            value='0',
                                            style={'width': '70px', 'display': 'inline-block'}
                                        ),
                                    ]),
                                ], className='d-flex align-items-center mb-2'),
                                
                                # Hidden field to store the generated cron
                                dcc.Store(id='edit-schedule-cron', data=monitor.get('schedule_cron', '0 0 0 * * ?')),
                                
                                # Show generated cron (optional)
                                dbc.FormText([
                                    "Generated cron: ",
                                    html.Code(id='cron-display', children=monitor.get('schedule_cron', '0 0 0 * * ?'))
                                ])
                            ], width=9)
                        ], className='mb-3'),
                        
                        # Enabled
                        dbc.Row([
                            dbc.Label("Status", width=3),
                            dbc.Col([
                                dbc.RadioItems(
                                    id='edit-enabled',
                                    options=[
                                        {'label': '✓ Enabled', 'value': True},
                                        {'label': '✗ Disabled', 'value': False}
                                    ],
                                    value=monitor.get('enabled', True),
                                    inline=True
                                )
                            ], width=9)
                        ], className='mb-4'),
                        
                        # Hidden fields for composite key
                        dcc.Store(id='edit-catalog', data=catalog),
                        dcc.Store(id='edit-schema', data=schema),
                        dcc.Store(id='edit-table', data=table),
                        
                        # Buttons
                        html.Div([
                            dbc.Button([html.I(className='fas fa-save me-2'), 'Save Changes'], 
                                      id='save-edit-btn', color='primary', className='me-2'),
                            dbc.Button([html.I(className='fas fa-times me-2'), 'Cancel'], 
                                      href='/config', color='secondary'),
                        ]),
                        
                        html.Div(id='edit-status', className='mt-3')
                    ])
                ])
            ], className='shadow'),
            
            # Custom Metrics Section (collapsible, below main edit form)
            dbc.Card([
                dbc.CardHeader(
                    html.Div([
                        html.I(className='fas fa-chevron-down me-2', id='custom-metrics-icon'),
                        html.I(className='fas fa-chart-line me-2'),
                        html.Span('Custom Metrics Configuration'),
                    ], id='collapse-custom-metrics-button', style={'cursor': 'pointer'}),
                    className='bg-light'
                ),
                dbc.Collapse(
                    dbc.CardBody([
                dbc.Row([
                    dbc.Col([
                        html.P('Manage custom data quality metrics for this table.', className='text-muted mb-3'),
                        dbc.Button([
                            html.I(className='fas fa-plus me-2'),
                            'Add New Custom Metric'
                        ], id='add-custom-metric-btn', color='success', size='sm', className='mb-3'),
                    ])
                ]),
                
                # Add Custom Metric Modal
                dbc.Modal([
                    dbc.ModalHeader(dbc.ModalTitle([
                        html.I(className='fas fa-plus-circle me-2'),
                        'Add New Custom Metric'
                    ])),
                    dbc.ModalBody([
                        html.Div(id='add-metric-form-content'),
                        html.Div(id='add-metric-status', className='mt-3')
                    ]),
                    dbc.ModalFooter([
                        dbc.Button("Cancel", id="add-metric-cancel", color="secondary", className="me-2"),
                        dbc.Button([
                            dbc.Spinner(size="sm", spinner_style={"display": "none"}, id="save-metric-spinner"),
                            html.I(className='fas fa-save me-2', id="save-metric-icon"),
                            html.Span("Save Metric", id="save-metric-text")
                        ], id="add-metric-save", color="primary"),
                    ]),
                    # Hidden interval for auto-refresh after save
                    dcc.Interval(id='refresh-after-save-interval', interval=2000, n_intervals=0, max_intervals=1, disabled=True)
                ], id='add-custom-metric-modal', size='lg', is_open=False),
                
                # Delete Confirmation Modal
                dbc.Modal([
                    dbc.ModalHeader(dbc.ModalTitle([
                        html.I(className='fas fa-exclamation-triangle me-2'),
                        'Confirm Delete'
                    ])),
                    dbc.ModalBody([
                        html.P([
                            "Are you sure you want to delete the metric ",
                            html.Strong(id='delete-metric-name-display'),
                            "? This action cannot be undone."
                        ]),
                        dbc.Alert([
                            html.I(className='fas fa-info-circle me-2'),
                            "This will also delete any associated detail metrics."
                        ], color='warning', className='mb-0')
                    ]),
                    dbc.ModalFooter([
                        dbc.Button("Cancel", id="cancel-delete-metric", color="secondary", className="me-2"),
                        dbc.Button([
                            html.I(className='fas fa-trash me-2'),
                            "Delete Metric"
                        ], id="confirm-delete-metric", color="danger"),
                    ]),
                    # Hidden interval for auto-refresh after delete
                    dcc.Interval(id='refresh-after-delete-interval', interval=1500, n_intervals=0, max_intervals=1, disabled=True)
                ], id='delete-confirmation-modal', is_open=False),
                
                # Hidden store for delete metric data
                dcc.Store(id='delete-metric-name', data=''),
                
                # Existing custom metrics table with loading spinner
                dcc.Loading(
                    id="loading-existing-custom-metrics",
                    type="default",
                    children=html.Div(id='existing-custom-metrics-section')
                )
                    ]),
                    id='collapse-custom-metrics',
                    is_open=False
                )
            ], className='shadow mt-3')
        ], fluid=True)
        
    except Exception as e:
        print(f"❌ Error loading monitor for edit: {e}")
        import traceback
        traceback.print_exc()
        return dbc.Container([
            dbc.Alert([
                html.H4("❌ Error Loading Monitor"),
                html.P(f"An error occurred: {str(e)}"),
                dbc.Button("Back to Configuration", href="/config", color="primary")
            ], color="danger")
        ], fluid=True)

def functions_catalog_layout():
    """Function Catalog page - displays all DQ functions with parsed metadata"""
    import pandas as pd
    import re
    
    try:
        # Get structured functions with metadata
        functions_data = db_utils.get_dq_functions_structured()
        ratio_functions = functions_data['ratio_functions']
        detail_functions = functions_data['detail_functions']
        
        if not ratio_functions and not detail_functions:
            return dbc.Container([
                html.H2([html.I(className='fas fa-book me-3'), 'Function Catalog'], className='mb-4'),
                dbc.Alert("No functions found", color="warning")
            ], fluid=True, className='mt-4')
        
        # Build ratio function cards with metadata
        ratio_cards = []
        for func in ratio_functions:
            # Build parameters display
            params_list = []
            for param in func['parameters']:
                params_list.append(
                    html.Li([
                        html.Code(param['name']),
                        f": {param['type']} ",
                        html.Small(f"- {param['comment']}", className='text-muted') if param['comment'] else ''
                    ])
                )
            
            # Create card for ratio function
            card_body_content = [
                html.P(func['description'], className='mb-2'),
                html.P([html.Strong("Returns: "), func['returns']], className='mb-2 small text-muted'),
            ]
            
            if params_list:
                card_body_content.append(
                    html.Div([
                        html.Strong("Parameters:"),
                        html.Ul(params_list, className='small')
                    ], className='mb-2')
                )
            
            if func['usage']:
                card_body_content.append(
                    html.Div([
                        html.Strong("Usage Example:"),
                        html.Code(func['usage'], className='d-block bg-light p-2 mt-1', style={'fontSize': '11px'})
                    ], className='mb-2')
                )
            
            if func['related_function']:
                card_body_content.append(
                    html.P([
                        html.I(className='fas fa-link me-1'),
                        html.Strong("Related: "),
                        html.Code(func['related_function'])
                    ], className='text-muted small')
                )
            
            # Add SQL definition
            func_def_df = db_utils.get_function_definition(func['name'])
            if not func_def_df.empty:
                func_sql = func_def_df.iloc[0]['routine_definition']
                card_body_content.append(
                    html.Div([
                        html.Strong("🔍 SQL Definition:"),
                        html.Details([
                            html.Summary("Click to view function source code", className='small text-primary mt-1', style={'cursor': 'pointer'}),
                            html.Pre(
                                func_sql,
                                className='small bg-dark text-white p-2 rounded mt-2',
                                style={
                                    'fontSize': '10px',
                                    'maxHeight': '200px',
                                    'overflow': 'auto',
                                    'fontFamily': 'Monaco, Consolas, monospace'
                                }
                            )
                        ])
                    ], className='mt-3')
                )
            
            ratio_cards.append(
                dbc.Card([
                    dbc.CardHeader(
                        html.H5([
                            html.I(className='fas fa-chart-line me-2'),
                            func['name'],
                            html.Span(' (Ratio Metric)', className='badge bg-primary ms-2', style={'fontSize': '0.7rem'})
                        ])
                    ),
                    dbc.CardBody(card_body_content)
                ], className='mb-3')
            )
        
        # Build detail function cards
        detail_cards = []
        for func in detail_functions:
            # Build parameters display
            params_list = []
            for param in func['parameters']:
                params_list.append(
                    html.Li([
                        html.Code(param['name']),
                        f": {param['type']} ",
                        html.Small(f"- {param['comment']}", className='text-muted') if param['comment'] else ''
                    ])
                )
            
            card_body_content = [
                html.P(func['description'], className='mb-2 small'),
            ]
            
            if params_list:
                card_body_content.append(
                    html.Div([
                        html.Strong("Parameters:"),
                        html.Ul(params_list, className='small')
                    ], className='mb-2')
                )
            
            if func['related_function']:
                card_body_content.append(
                    html.P([
                        html.I(className='fas fa-link me-1'),
                        html.Strong("Related: "),
                        html.Code(func['related_function'])
                    ], className='text-muted small')
                )
            
            # Add SQL definition for detail functions too
            func_def_df = db_utils.get_function_definition(func['name'])
            if not func_def_df.empty:
                func_sql = func_def_df.iloc[0]['routine_definition']
                card_body_content.append(
                    html.Div([
                        html.Strong("🔍 SQL Definition:"),
                        html.Details([
                            html.Summary("Click to view function source code", className='small text-primary mt-1', style={'cursor': 'pointer'}),
                            html.Pre(
                                func_sql,
                                className='small bg-dark text-white p-2 rounded mt-2',
                                style={
                                    'fontSize': '10px',
                                    'maxHeight': '200px',
                                    'overflow': 'auto',
                                    'fontFamily': 'Monaco, Consolas, monospace'
                                }
                            )
                        ])
                    ], className='mt-2')
                )
            
            detail_cards.append(
                dbc.Card([
                    dbc.CardHeader(
                        html.H6([
                            html.I(className='fas fa-microscope me-2'),
                            func['name'],
                            html.Span(' (Detail Metric)', className='badge bg-secondary ms-2', style={'fontSize': '0.6rem'})
                        ])
                    ),
                    dbc.CardBody(card_body_content)
                ], className='mb-2')
            )
        
        return dbc.Container([
            html.H2([html.I(className='fas fa-book me-3'), 'Function Catalog'], className='mb-4'),
            html.P([
                'Browse all available data quality functions. ',
                f'Found {len(ratio_functions) + len(detail_functions)} functions: ',
                html.Strong(f'{len(ratio_functions)} ratio metrics', className='text-primary'),
                ' and ',
                html.Strong(f'{len(detail_functions)} detail metrics', className='text-secondary'),
                '.'
            ]),
            html.Hr(),
            
            # Ratio Functions Section
            html.H3([html.I(className='fas fa-chart-line me-2'), 'Ratio Metrics'], className='mt-4 mb-3'),
            html.P('These are the main data quality metrics that calculate ratios or percentages. Use these when adding custom metrics.', className='text-muted'),
            html.Div(ratio_cards if ratio_cards else dbc.Alert("No ratio functions found", color="info")),
            
            # Detail Functions Section
            html.H3([html.I(className='fas fa-microscope me-2'), 'Detail/Supporting Metrics'], className='mt-5 mb-3'),
            html.P('These are supporting functions automatically used by ratio metrics to provide drill-down details.', className='text-muted'),
            html.Div(detail_cards if detail_cards else dbc.Alert("No detail functions found", color="info"))
        ], fluid=True, className='mt-4')
        
    except Exception as e:
        print(f"❌ Error loading functions: {e}")
        import traceback
        traceback.print_exc()
        return dbc.Container([
            dbc.Alert([
                html.H4("❌ Error"),
                html.P(f"An error occurred: {str(e)}")
            ], color="danger")
        ])

# Router callback
@callback(
    Output('page-content', 'children'),
    Input('url', 'pathname')
)
def display_page(pathname):
    try:
        if pathname == '/config':
            return config_layout()
        elif pathname == '/functions':
            # Function Catalog page
            return functions_catalog_layout()
        elif pathname and pathname.startswith('/config/edit/'):
            # Parse the path: /config/edit/{catalog}/{schema}/{table}
            parts = pathname.split('/')
            if len(parts) >= 6:
                catalog, schema, table = parts[3], parts[4], parts[5]
                return edit_monitor_layout(catalog, schema, table)
            else:
                return dbc.Container([
                    dbc.Alert("Invalid edit URL", color="danger")
                ], fluid=True)
        else:  # Default to dashboard (including '/')
            return dashboard_layout()
    except Exception as e:
        print(f"Error in display_page: {e}")
        import traceback
        traceback.print_exc()
        return dbc.Container([
            dbc.Alert([
                html.H4("Error Loading Page"),
                html.P(f"An error occurred: {str(e)}"),
                dbc.Button("Go to Dashboard", href="/", color="primary")
            ], color="danger")
        ])

# Enable/disable edit button based on row selection
@callback(
    Output('edit-monitor-btn', 'disabled'),
    Input('monitors-table', 'selected_rows')
)
def toggle_edit_button(selected_rows):
    """Enable edit button when a row is selected"""
    return not selected_rows or len(selected_rows) == 0

# Toggle table preview collapse
@callback(
    [Output('collapse-preview', 'is_open'),
     Output('preview-icon', 'className')],
    Input('collapse-preview-button', 'n_clicks'),
    State('collapse-preview', 'is_open'),
    prevent_initial_call=True
)
def toggle_preview_collapse(n_clicks, is_open):
    """Toggle table preview section and change icon"""
    if n_clicks:
        new_state = not is_open
        icon_class = 'fas fa-chevron-up me-2' if new_state else 'fas fa-chevron-down me-2'
        return new_state, icon_class
    return is_open, 'fas fa-chevron-down me-2'

# Toggle custom metrics collapse
@callback(
    [Output('collapse-custom-metrics', 'is_open'),
     Output('custom-metrics-icon', 'className')],
    Input('collapse-custom-metrics-button', 'n_clicks'),
    State('collapse-custom-metrics', 'is_open'),
    prevent_initial_call=True
)
def toggle_custom_metrics_collapse(n_clicks, is_open):
    """Toggle custom metrics section and change icon"""
    if n_clicks:
        new_state = not is_open
        icon_class = 'fas fa-chevron-up me-2' if new_state else 'fas fa-chevron-down me-2'
        return new_state, icon_class
    return is_open, 'fas fa-chevron-down me-2'

# Load existing custom metrics when section is opened
@callback(
    Output('existing-custom-metrics-section', 'children'),
    [Input('collapse-custom-metrics', 'is_open'),
     Input('url', 'pathname')]
)
def load_existing_custom_metrics(is_open, pathname):
    """Load and display existing custom metrics for the table"""
    if not is_open:
        return html.Div()
    
    # Extract table info from URL
    try:
        parts = pathname.split('/')
        if len(parts) >= 6 and parts[2] == 'edit':
            catalog = parts[3]
            schema = parts[4]
            table = parts[5]
            
            # DEBUG: First, let's see ALL metric names in the database
            all_metric_names = db_utils.get_all_metric_names_for_table(schema, table)
            
            # Query all custom metrics (including details)
            df_all_metrics = db_utils.get_custom_metrics_for_table(schema, table, include_details=True)
            df_ratio_metrics = db_utils.get_custom_metrics_for_table(schema, table, include_details=False)
            
            # Keep a copy of the raw data before formatting (for accessing arrays/dicts)
            df_ratio_metrics_raw = df_ratio_metrics.copy()
            
            # DEBUG: Print metric names BEFORE prepare_dataframe_for_table
            print(f"\n📊 DEBUG - All metrics BEFORE formatting ({len(df_all_metrics)} total):")
            if 'metric_name' in df_all_metrics.columns:
                for idx, name in enumerate(df_all_metrics['metric_name'].tolist(), 1):
                    print(f"   {idx}. {name}")
            
            print(f"\n📊 DEBUG - Ratio metrics BEFORE formatting ({len(df_ratio_metrics)} total):")
            if 'metric_name' in df_ratio_metrics.columns:
                for idx, name in enumerate(df_ratio_metrics['metric_name'].tolist(), 1):
                    print(f"   {idx}. {name}")
            
            # Prepare dataframes for display
            df_all_metrics = prepare_dataframe_for_table(df_all_metrics.copy())
            df_ratio_metrics = prepare_dataframe_for_table(df_ratio_metrics.copy())
            
            # DEBUG: Print column names AFTER prepare_dataframe_for_table
            print(f"\n📊 DEBUG - Columns AFTER formatting:")
            print(f"   All metrics columns: {df_all_metrics.columns.tolist()}")
            print(f"   Ratio metrics columns: {df_ratio_metrics.columns.tolist()}")
            
            if df_ratio_metrics.empty:
                return dbc.Alert([
                    html.I(className='fas fa-info-circle me-2'),
                    'No custom metrics configured for this table yet. Click "Add New Custom Metric" to create one.'
                ], color='info')
            
            # Build grouped display - ratio metrics with their details
            # Pre-fetch function definitions and parameters by extracting function names from definition templates
            function_definitions = {}
            function_parameters = {}
            print(f"\n🔍 Pre-fetching function definitions and parameters...")
            for idx, row in df_ratio_metrics_raw.iterrows():
                template_name = row.get('Template', 'N/A')
                definition_template = row.get('Definition', 'N/A')
                
                # Extract actual function name from the SQL definition
                func_name = extract_function_name(definition_template)
                
                if func_name and template_name not in function_definitions:
                    print(f"   Template: {template_name}")
                    print(f"      Extracted function: {func_name}")
                    
                    # Fetch function definition
                    func_def_df = db_utils.get_function_definition(func_name)
                    if not func_def_df.empty:
                        func_def = func_def_df.iloc[0]['routine_definition']
                        function_definitions[template_name] = func_def
                        print(f"      ✅ Found definition ({len(func_def)} chars)")
                    else:
                        print(f"      ❌ No definition found")
                    
                    # Fetch function parameters
                    params = db_utils.get_function_parameters(func_name)
                    if params:
                        function_parameters[template_name] = params
                        print(f"      ✅ Found {len(params)} parameters")
                    else:
                        print(f"      ⚠️ No parameters found")
            print(f"   Total definitions cached: {len(function_definitions)}")
            print(f"   Total parameter signatures cached: {len(function_parameters)}")
            
            metric_cards = []
            for i, (idx, ratio_row) in enumerate(df_ratio_metrics.iterrows()):
                ratio_name = ratio_row['Metric Name']
                # Get the corresponding raw row for accessing arrays/dicts
                ratio_row_raw = df_ratio_metrics_raw.iloc[i]
                template_name = ratio_row['Template'] if 'Template' in ratio_row.index else 'N/A'
                func_definition = function_definitions.get(template_name, None)
                
                print(f"\n   Building card for: {ratio_name}")
                print(f"      Template: {template_name}")
                print(f"      Has function definition: {func_definition is not None}")
                print(f"      🔧 DELETE BUTTON ID: {{'type': 'delete-metric', 'index': '{ratio_name}'}}")
                
                # Find associated detail metric
                # Pattern: 
                #   Ratio metric: "missing_value_ratio_customer_id"
                #   Detail metric: "missing_value_ratio_customer_id_details_json"
                # So detail name = ratio name + "_details_json"
                
                detail_row = pd.DataFrame()  # Empty by default
                detail_name = f"{ratio_name}_details_json"
                
                # Fetch detail metric directly from DB (not from prepared dataframe) to get raw data
                detail_row = db_utils.get_detail_metric_for_ratio(schema, table, ratio_name)
                
                print(f"🔍 Ratio: '{ratio_name}' → Detail: '{detail_name}' → Found: {not detail_row.empty}")
                
                if not detail_row.empty:
                    print(f"   Columns: {detail_row.iloc[0]['Input Columns'] if 'Input Columns' in detail_row.columns else 'N/A'}")
                
                # Build metric card
                metric_cards.append(
                    dbc.Card([
                        dbc.CardBody([
                            # Main metric info
                            html.Div([
                                html.H6([
                                    html.I(className='fas fa-chart-line me-2'),
                                    ratio_name
                                ], className='mb-2'),
                                dbc.Row([
                                    dbc.Col([
                                        dbc.Badge(ratio_row['Dimension'], color='info', className='me-2'),
                                        dbc.Badge(ratio_row['Status'], 
                                                 color='success' if 'Enabled' in ratio_row['Status'] else 'secondary',
                                                 className='me-2'),
                                        dbc.Badge([
                                            html.I(className='fas fa-microscope me-1'),
                                            'Detail Capture: ',
                                            html.I(className='fas fa-check-circle') if not detail_row.empty else html.I(className='fas fa-times-circle')
                                        ], 
                                        color='success' if not detail_row.empty else 'secondary',
                                        className='me-2')
                                    ], width='auto')
                                ]),
                                # Business-friendly description
                                dbc.Alert([
                                    html.Div([
                                        html.I(className='fas fa-info-circle me-2'),
                                        html.Strong("What this checks: ", className='me-1'),
                                        html.Span(ratio_row['Description'])
                                    ])
                                ], color='light', className='mb-3 py-2 px-3 border'),
                                
                                # Monitored Columns - Display actual bound column values
                                html.Div([
                                    html.Div([
                                        html.I(className='fas fa-table me-2', style={'color': '#0d6efd'}),
                                        html.Strong("Monitored Columns", className='mb-2')
                                    ], className='mb-2'),
                                    (lambda bound_params:
                                        dbc.Table([
                                            html.Thead([
                                                html.Tr([
                                                    html.Th("Placeholder", style={'width': '40%', 'backgroundColor': '#f8f9fa'}),
                                                    html.Th("Column", style={'width': '60%', 'backgroundColor': '#f8f9fa'})
                                                ])
                                            ]),
                                            html.Tbody([
                                                html.Tr([
                                                    html.Td(
                                                        html.Code(param_name, className='px-2 py-1',
                                                                style={'backgroundColor': '#fff3bf', 'color': '#856404', 'borderRadius': '4px'}),
                                                        style={'fontWeight': '500'}
                                                    ),
                                                    html.Td(
                                                        html.Code(column_value, className='px-2 py-1',
                                                                style={'backgroundColor': '#e7f5ff', 'color': '#1971c2', 'borderRadius': '4px'}),
                                                        style={'fontWeight': '500'}
                                                    )
                                                ]) for param_name, column_value in bound_params.items()
                                            ]) if bound_params else html.Tbody([
                                                html.Tr([
                                                    html.Td("No parameters bound", colSpan=2, className='text-center text-muted')
                                                ])
                                            ])
                                        ], bordered=True, hover=True, size='sm', className='mb-0')
                                    )(
                                        (lambda p: dict(p) if isinstance(p, list) else p if isinstance(p, dict) else {})(ratio_row_raw.get('Parameters', {}))
                                    )
                                ], className='mb-3'),
                                
                                # Quality Thresholds - More visual
                                html.Div([
                                    html.Div([
                                        html.I(className='fas fa-chart-bar me-2', style={'color': '#37b24d'}),
                                        html.Strong("Quality Thresholds", className='mb-2')
                                    ], className='mb-2'),
                                    html.Div(ratio_row['Quality Thresholds'], className='small ps-3', 
                                             style={'whiteSpace': 'pre-line', 'fontSize': '13px', 'lineHeight': '2'})
                                ], className='mb-3'),
                                
                                # Advanced/Technical Details - Collapsed by default
                                html.Details([
                                    html.Summary([
                                        html.I(className='fas fa-cog me-2'),
                                        html.Strong("Advanced Technical Details", className='text-muted')
                                    ], style={'cursor': 'pointer', 'padding': '8px', 'backgroundColor': '#f8f9fa', 'borderRadius': '4px'}),
                                    html.Div([
                                        # Function name
                                        html.Div([
                                            html.Strong("Function Template:", className='small d-block mb-1 text-muted'),
                                            html.Code(template_name, className='small d-block')
                                        ], className='mb-3 mt-3'),
                                        
                                        # SQL Function Call
                                        html.Div([
                                            html.Strong("Generated SQL:", className='small d-block mb-1 text-muted'),
                                            html.Pre(
                                                substitute_parameters(
                                                    ratio_row.get('Definition', 'N/A') if 'Definition' in ratio_row.index else 'N/A',
                                                    ratio_row_raw.get('Parameters', {})
                                                ),
                                                className='small bg-white p-2 rounded border',
                                                style={'fontSize': '11px', 'maxHeight': '100px', 'overflow': 'auto', 'fontFamily': 'Monaco, monospace'}
                                            )
                                        ], className='mb-3'),
                                        
                                        # SQL Function Body (with actual column substitution)
                                        html.Div([
                                            html.Strong("Function Implementation (SQL):", className='small d-block mb-1 text-muted'),
                                            html.Pre(
                                                substitute_function_params(
                                                    func_definition if func_definition else 'Not available',
                                                    function_parameters.get(template_name, []),
                                                    ratio_row_raw.get('Parameters', {})
                                                ),
                                                className='small bg-dark text-white p-2 rounded',
                                                style={
                                                    'fontSize': '10px',
                                                    'maxHeight': '150px',
                                                    'overflow': 'auto',
                                                    'fontFamily': 'Monaco, Consolas, monospace'
                                                }
                                            )
                                        ]) if func_definition else html.Div()
                                    ], className='p-2')
                                ], className='mb-2'),
                            ]),
                            
                            # Actions
                            html.Hr(className='my-2'),
                            html.Div([
                                dbc.Button([html.I(className='fas fa-trash me-1'), 'Delete'], 
                                          id={'type': 'delete-metric', 'index': ratio_name},
                                          size='sm', color='danger', outline=True),
                            ], className='text-end')
                        ])
                    ], className='mb-3')
                )
            
            return html.Div([
                html.Div([
                    html.H6([
                        html.I(className='fas fa-list me-2'),
                        f'Custom Metrics ({len(df_ratio_metrics)})'
                    ], className='mb-3')
                ]),
                html.Div(metric_cards)
            ])
            
    except Exception as e:
        print(f"❌ Error loading custom metrics: {e}")
        import traceback
        traceback.print_exc()
        return dbc.Alert([
            html.H6("❌ Error Loading Custom Metrics"),
            html.P(f"An error occurred: {str(e)}")
        ], color='danger')
    
    return html.Div()

# Open/close Add Custom Metric modal
@callback(
    Output('add-custom-metric-modal', 'is_open'),
    [Input('add-custom-metric-btn', 'n_clicks'),
     Input('add-metric-cancel', 'n_clicks')],
    State('add-custom-metric-modal', 'is_open'),
    prevent_initial_call=True
)
def toggle_add_metric_modal(open_clicks, cancel_clicks, is_open):
    """Toggle the Add Custom Metric modal"""
    return not is_open

# Load form content when modal opens
@callback(
    Output('add-metric-form-content', 'children'),
    [Input('add-custom-metric-modal', 'is_open'),
     Input('url', 'pathname')],
    prevent_initial_call=True
)
def load_add_metric_form(is_open, pathname):
    """Load the Add Custom Metric form with template selector"""
    if not is_open:
        return html.Div()
    
    try:
        # Get table info from URL
        parts = pathname.split('/')
        if len(parts) >= 6 and parts[2] == 'edit':
            catalog = parts[3]
            schema = parts[4]
            table = parts[5]
            
            # Get available metric templates (ratio templates only, exclude detail templates)
            templates_query = f"""
            SELECT template_name, description, dimension, 
                   good_threshold, acceptable_threshold, threshold_direction
            FROM {CATALOG}.{ADMIN_SCHEMA}.metric_templates
            WHERE dimension IS NOT NULL
            ORDER BY dimension, template_name
            """
            df_templates = db_utils.execute_query(templates_query)
            
            # Create template options for dropdown grouped by dimension
            template_options = [
                {'label': f"{row['template_name']} ({row['dimension']}) - {row['description'][:80]}...", 
                 'value': row['template_name']}
                for _, row in df_templates.iterrows()
            ]
            
            return html.Div([
                # Template selector
                dbc.Row([
                    dbc.Label("Select DQ Template", width=12, className='fw-bold'),
                    dbc.Col([
                        dbc.Select(
                            id='add-metric-function-select',  # Keep same ID for compatibility
                            options=template_options,
                            placeholder='Choose a data quality template...'
                        ),
                        dbc.FormText([
                            html.I(className='fas fa-book me-1'),
                            html.A('Browse Function Catalog', href='/functions', target='_blank')
                        ])
                    ], width=12)
                ], className='mb-3'),
                
                # Dynamic form content based on function selection
                html.Div(id='add-metric-dynamic-form'),
                
                # Hidden stores for table info
                dcc.Store(id='add-metric-catalog', data=catalog),
                dcc.Store(id='add-metric-schema', data=schema),
                dcc.Store(id='add-metric-table', data=table),
            ])
            
    except Exception as e:
        print(f"❌ Error loading add metric form: {e}")
        import traceback
        traceback.print_exc()
        return dbc.Alert([
            html.H6("Error"),
            html.P(f"Could not load form: {str(e)}")
        ], color='danger')

# Generate dynamic form based on selected function
@callback(
    Output('add-metric-dynamic-form', 'children'),
    [Input('add-metric-function-select', 'value'),
     Input('add-metric-catalog', 'data'),
     Input('add-metric-schema', 'data'),
     Input('add-metric-table', 'data')],
    prevent_initial_call=True
)
def generate_metric_form(template_name, catalog, schema, table):
    """Generate parameter mapping form based on selected template"""
    if not template_name or not catalog or not schema or not table:
        return html.Div()
    
    try:
        # Get template details including thresholds
        template_query = f"""
        SELECT mt.*, mt.definition_template
        FROM {CATALOG}.{ADMIN_SCHEMA}.metric_templates mt
        WHERE mt.template_name = '{template_name}'
        """
        df_template = db_utils.execute_query(template_query)
        
        if df_template.empty:
            return dbc.Alert("Template not found", color="warning")
        
        template_row = df_template.iloc[0]
        
        # Convert Series to dict for easier access and to avoid Series type issues
        template_dict = template_row.to_dict()
        
        # Extract function name from definition_template
        # Example: "avg(schema.function_name({{PARAM}}))" -> extract "function_name"
        import re
        definition = str(template_dict['definition_template'])
        func_match = re.search(r'\.([a-z_]+)\(', definition)
        function_name = func_match.group(1) if func_match else None
        
        if not function_name:
            return dbc.Alert("Could not extract function from template", color="warning")
        
        # Get function details for parameters
        functions_data = db_utils.get_dq_functions_structured()
        selected_function = next((f for f in functions_data['ratio_functions'] if f['name'] == function_name), None)
        
        if not selected_function:
            return dbc.Alert("Function not found", color="warning")
        
        # Get table columns with types
        column_query = f"DESCRIBE {catalog}.{schema}.{table}"
        df_columns = db_utils.execute_query(column_query)
        
        # Build form elements
        form_elements = []
        
        # Template description
        form_elements.append(
            dbc.Alert([
                html.Div([
                    html.Strong(template_name),
                    dbc.Badge(str(template_dict.get('dimension', 'N/A')), color='primary', className='ms-2')
                ]),
                html.P(str(template_dict.get('description', '')), className='mb-1 mt-2'),
                html.Small([
                    html.Strong("Function: "),
                    html.Code(function_name),
                    html.Br(),
                    html.Strong("Usage: "),
                    html.Code(selected_function['usage'])
                ], className='text-muted')
            ], color='info', className='mb-3')
        )
        
        # Parameter mapping
        for param in selected_function['parameters']:
            param_name = param['name']
            param_type = param['type']
            param_comment = param['comment']
            
            # Filter columns by type compatibility
            if 'DATE' in param_type.upper():
                compatible_columns = df_columns[df_columns['data_type'].str.contains('date|timestamp', case=False, na=False)]
            elif 'TIMESTAMP' in param_type.upper():
                compatible_columns = df_columns[df_columns['data_type'].str.contains('timestamp', case=False, na=False)]
            elif 'INT' in param_type.upper():
                compatible_columns = df_columns[df_columns['data_type'].str.contains('int|long|short|byte', case=False, na=False)]
            elif 'DOUBLE' in param_type.upper() or 'DECIMAL' in param_type.upper():
                compatible_columns = df_columns[df_columns['data_type'].str.contains('double|decimal|float', case=False, na=False)]
            elif 'BOOLEAN' in param_type.upper():
                compatible_columns = df_columns[df_columns['data_type'].str.contains('boolean', case=False, na=False)]
            else:  # STRING or ANY
                compatible_columns = df_columns
            
            column_options = [
                {'label': f"{row['col_name']} ({row['data_type']})", 'value': row['col_name']}
                for _, row in compatible_columns.iterrows()
            ]
            
            form_elements.append(
                dbc.Row([
                    dbc.Label(param_name, width=3, className='text-capitalize'),
                    dbc.Col([
                        dbc.Select(
                            id={'type': 'add-metric-param', 'param': param_name},
                            options=column_options,
                            placeholder=f'Select column ({param_type})',
                            className='metric-param-select',  # Add class for easier selection
                        ),
                        dbc.FormText(param_comment) if param_comment else None
                    ], width=9)
                ], className='mb-3')
            )
        
        # Metric name (auto-generated from template + column name, but editable)
        form_elements.append(html.Hr())
        
        # Store template name for callback
        form_elements.append(dcc.Store(id='add-metric-template-name', data=template_name))
        
        form_elements.append(
            dbc.Row([
                dbc.Label("Metric Name", width=3, className='fw-bold'),
                dbc.Col([
                    dbc.Input(
                        id='add-metric-name',
                        type='text',
                        placeholder=f'{template_name}_column_name',
                        value=f'{template_name}'
                    ),
                    dbc.FormText("Auto-generated as: template_name + _ + column_name (editable)")
                ], width=9)
            ], className='mb-3')
        )
        
        # Thresholds (pre-populated from template, converted to percentages)
        # Extract values from dict
        good_threshold_val = template_dict.get('good_threshold')
        acceptable_threshold_val = template_dict.get('acceptable_threshold')
        
        # Convert to percentages, handling None/null values
        if good_threshold_val is not None and not pd.isna(good_threshold_val):
            good_threshold_pct = float(good_threshold_val) * 100
        else:
            good_threshold_pct = 1.0
            
        if acceptable_threshold_val is not None and not pd.isna(acceptable_threshold_val):
            acceptable_threshold_pct = float(acceptable_threshold_val) * 100
        else:
            acceptable_threshold_pct = 5.0
        
        threshold_direction = template_dict.get('threshold_direction', 'LOWER_IS_BETTER')
        if not threshold_direction or pd.isna(threshold_direction):
            threshold_direction = 'LOWER_IS_BETTER'
        
        # Format thresholds for display (read-only, from template)
        if threshold_direction == 'LOWER_IS_BETTER':
            threshold_display = f"✅ Good < {good_threshold_pct:.1f}%\n⚠️ Acceptable < {acceptable_threshold_pct:.1f}%\n❌ Bad ≥ {acceptable_threshold_pct:.1f}%"
        elif threshold_direction == 'HIGHER_IS_BETTER':
            threshold_display = f"✅ Good > {good_threshold_pct:.1f}%\n⚠️ Acceptable > {acceptable_threshold_pct:.1f}%\n❌ Bad ≤ {acceptable_threshold_pct:.1f}%"
        else:
            threshold_display = f"✅ Good: {good_threshold_pct:.1f}%\n⚠️ Acceptable: {acceptable_threshold_pct:.1f}%"
        
        form_elements.append(
            dbc.Row([
                dbc.Label("Quality Thresholds", width=3, className='fw-bold'),
                dbc.Col([
                    dbc.Alert([
                        html.Div([
                            html.Strong("From Template (Read-Only)"),
                            html.Div(threshold_display, style={'whiteSpace': 'pre-line', 'marginTop': '8px', 'lineHeight': '1.8'})
                        ])
                    ], color='info', className='py-3'),
                    # Hidden inputs to store threshold values for form submission
                    dbc.Input(id='add-metric-good-threshold', type='hidden', value=good_threshold_val),
                    dbc.Input(id='add-metric-acceptable-threshold', type='hidden', value=acceptable_threshold_val),
                ], width=9)
            ], className='mb-3')
        )
        
        # Detail Capture Configuration (optional)
        form_elements.append(html.Hr())
        form_elements.append(
            html.H6([
                html.I(className='fas fa-microscope me-2'),
                'Detail Capture (Optional)'
            ], className='mb-3')
        )
        
        form_elements.append(
            dbc.Row([
                dbc.Label("Capture Violated Rows", width=3),
                dbc.Col([
                    dbc.Switch(
                        id='add-metric-enable-details',
                        value=False,
                        className='mb-2'
                    ),
                    dbc.FormText("Enable to capture details of rows that violate this quality check for drill-down analysis")
                ], width=9)
            ], className='mb-3')
        )
        
        # Detail configuration (shown when switch is enabled)
        detail_config = dbc.Collapse([
            dbc.Alert([
                html.Strong("Detail Capture Configuration"),
                html.P("Select columns to include in the detail records for failed quality checks.", className='mb-0 mt-1 small')
            ], color='light', className='mb-3'),
            
            dbc.Row([
                dbc.Label("Primary Key Column(s)", width=3),
                dbc.Col([
                    dcc.Dropdown(
                        id='add-metric-detail-pk-cols',
                        options=[{'label': f"{row['col_name']} ({row['data_type']})", 'value': row['col_name']} 
                                for _, row in df_columns.iterrows()],
                        multi=True,
                        placeholder='Select primary key column(s)'
                    ),
                    dbc.FormText("Used to identify specific failing rows")
                ], width=9)
            ], className='mb-3'),
            
            dbc.Row([
                dbc.Label("Additional Context Columns", width=3),
                dbc.Col([
                    dcc.Dropdown(
                        id='add-metric-detail-context-cols',
                        options=[{'label': f"{row['col_name']} ({row['data_type']})", 'value': row['col_name']} 
                                for _, row in df_columns.iterrows()],
                        multi=True,
                        placeholder='Select additional columns (optional)'
                    ),
                    dbc.FormText("Additional columns to help understand why the check failed")
                ], width=9)
            ], className='mb-3'),
        ], id='add-metric-detail-config', is_open=False)
        
        form_elements.append(detail_config)
        
        # Enable/Disable
        form_elements.append(html.Hr())
        form_elements.append(
            dbc.Row([
                dbc.Label("Status", width=3, className='fw-bold'),
                dbc.Col([
                    dbc.RadioItems(
                        id='add-metric-enabled',
                        options=[
                            {'label': '✓ Enabled', 'value': True},
                            {'label': '✗ Disabled', 'value': False}
                        ],
                        value=True,
                        inline=True
                    )
                ], width=9)
            ], className='mb-3')
        )
        
        return html.Div(form_elements)
        
    except Exception as e:
        print(f"❌ Error generating metric form: {e}")
        import traceback
        traceback.print_exc()
        return dbc.Alert([
            html.H6("Error"),
            html.P(f"Could not generate form: {str(e)}")
        ], color='danger')

# Toggle detail capture configuration
@callback(
    Output('add-metric-detail-config', 'is_open'),
    Input('add-metric-enable-details', 'value'),
    prevent_initial_call=True
)
def toggle_detail_config(enabled):
    """Show/hide detail capture configuration based on switch"""
    return enabled

# Auto-generate metric name from template + first selected column
@callback(
    Output('add-metric-name', 'value', allow_duplicate=True),
    [Input({'type': 'add-metric-param', 'param': ALL}, 'value')],
    [State('add-metric-template-name', 'data')],
    prevent_initial_call=True
)
def auto_generate_metric_name(param_values, template_name):
    """Auto-generate metric name: template_name + _ + first_column_name"""
    print(f"\n🔍 Auto-generate metric name callback triggered")
    print(f"  Template: {template_name}")
    print(f"  Param values: {param_values}")
    
    if not template_name:
        print("  ❌ No template name")
        return no_update
    
    # Get first non-empty parameter value
    first_column = None
    for val in param_values:
        if val:
            first_column = val
            break
    
    if first_column:
        generated_name = f"{template_name}_{first_column}"
        print(f"  ✅ Generated name: {generated_name}")
        return generated_name
    else:
        print(f"  ⚠️ No column selected yet, keeping template name")
        return template_name

# Save new custom metric - simplified to avoid conflicts
@callback(
    [Output('add-custom-metric-modal', 'is_open', allow_duplicate=True),
     Output('add-metric-status', 'children', allow_duplicate=True),
     Output('refresh-after-save-interval', 'disabled', allow_duplicate=True),
     Output('toast-container', 'children', allow_duplicate=True)],
    Input('add-metric-save', 'n_clicks'),
    [State('add-metric-function-select', 'value'),
     State({'type': 'add-metric-param', 'param': ALL}, 'value'),
     State('add-metric-name', 'value'),
     State('add-metric-good-threshold', 'value'),
     State('add-metric-acceptable-threshold', 'value'),
     State('add-metric-enabled', 'value'),
     State('add-metric-enable-details', 'value'),
     State('add-metric-detail-pk-cols', 'value'),
     State('add-metric-detail-context-cols', 'value'),
     State('add-metric-schema', 'data'),
     State('add-metric-table', 'data'),
     State('url', 'pathname')],
    prevent_initial_call=True
)
def save_new_custom_metric(n_clicks, template_name, param_values, metric_name, good_threshold, acceptable_threshold, enabled, 
                           enable_details, detail_pk_cols, detail_context_cols, schema, table, pathname):
    """Save the new custom metric to metric_bindings table"""
    print(f"\n{'='*80}")
    print(f"🔍 SAVE CALLBACK TRIGGERED")
    print(f"   n_clicks: {n_clicks}")
    print(f"   template_name: {template_name}")
    print(f"   metric_name: {metric_name}")
    print(f"{'='*80}\n")
    
    if not n_clicks or not template_name:
        print("❌ Validation failed: no clicks or no template name")
        return True, html.Div(), True, html.Div()
    
    try:
        # Get template details to extract function name
        template_query = f"""
        SELECT definition_template 
        FROM {CATALOG}.{ADMIN_SCHEMA}.metric_templates
        WHERE template_name = '{template_name}'
        """
        df_template = db_utils.execute_query(template_query)
        
        if df_template.empty:
            print(f"❌ Template '{template_name}' not found")
            return False, html.Div(), True, html.Div()
        
        # Extract function name and placeholders from definition_template
        import re
        definition = str(df_template.iloc[0]['definition_template'])
        func_match = re.search(r'\.([a-z_]+)\(', definition)
        function_name = func_match.group(1) if func_match else None
        
        if not function_name:
            print(f"❌ Could not extract function name from template")
            return False, html.Div(), True, html.Div()
        
        print(f"   Extracted function_name: {function_name}")
        
        # Extract placeholder names from template (e.g., {{VAL_COL}}, {{PK}})
        placeholder_pattern = r'\{\{([A-Z_]+)\}\}'
        template_placeholders = re.findall(placeholder_pattern, definition)
        print(f"   Template placeholders: {template_placeholders}")
        
        # Get function details to determine parameter order
        functions_data = db_utils.get_dq_functions_structured()
        selected_function = next((f for f in functions_data['ratio_functions'] if f['name'] == function_name), None)
        
        if not selected_function:
            print(f"❌ Function '{function_name}' not found in catalog")
            return False, html.Div(), True, html.Div()
        
        # Map template placeholder names to column values (using template placeholders, not function param names)
        input_columns = {}
        for i, param in enumerate(selected_function['parameters']):
            if i < len(param_values) and param_values[i]:
                # Use the template placeholder name (uppercase) instead of function parameter name (lowercase)
                if i < len(template_placeholders):
                    placeholder_name = template_placeholders[i]
                    input_columns[placeholder_name] = param_values[i]
                    print(f"   Mapping {placeholder_name} -> {param_values[i]}")
        
        # Validate all parameters are filled
        if len(input_columns) != len(template_placeholders):
            print(f"❌ Not all parameters filled: {len(input_columns)} of {len(template_placeholders)}")
            return False, html.Div(), True, html.Div()
        
        # Convert percentage values to decimals for storage
        good_threshold_decimal = good_threshold / 100.0 if good_threshold is not None else 0.01
        acceptable_threshold_decimal = acceptable_threshold / 100.0 if acceptable_threshold is not None else 0.05
        
        # Save to database (function_name parameter is actually template_name in db_utils)
        success = db_utils.save_custom_metric(
            schema=schema,
            table=table,
            metric_name=metric_name,
            function_name=template_name,  # This goes to template_name column
            input_columns=input_columns,
            good_threshold=good_threshold_decimal,
            acceptable_threshold=acceptable_threshold_decimal,
            enabled=enabled
        )
        
        # If detail capture is enabled, also save the detail metric
        print(f"\n📋 Detail capture check:")
        print(f"   success: {success}")
        print(f"   enable_details: {enable_details}")
        print(f"   detail_pk_cols: {detail_pk_cols}")
        
        if success and enable_details and detail_pk_cols:
            print(f"✅ Creating detail metric...")
            
            # Find the related detail template
            # Remove "_ratio" suffix and add "_details_json"
            # E.g., "missing_value_ratio" -> "missing_value_details_json"
            base_template = template_name.replace('_ratio', '').replace('_rate', '').replace('_pct', '')
            detail_template_name = f"{base_template}_details_json"
            print(f"   Base template: {base_template}")
            print(f"   Looking for detail template: {detail_template_name}")
            
            # Get detail template definition
            detail_template_query = f"""
            SELECT definition_template 
            FROM {CATALOG}.{ADMIN_SCHEMA}.metric_templates
            WHERE template_name = '{detail_template_name}'
            """
            df_detail_template = db_utils.execute_query(detail_template_query)
            print(f"   Detail template query returned {len(df_detail_template)} rows")
            print(f"   Detail template found: {not df_detail_template.empty}")
            
            if not df_detail_template.empty:
                print(f"   ✅ Proceeding with detail metric creation...")
                # Extract placeholders from detail template
                detail_definition = str(df_detail_template.iloc[0]['definition_template'])
                detail_placeholders = re.findall(placeholder_pattern, detail_definition)
                print(f"   Detail template placeholders: {detail_placeholders}")
                
                # Map placeholders to columns
                detail_columns = {}
                
                # Map PK placeholder (Primary Key Column)
                if 'PK' in detail_placeholders and detail_pk_cols:
                    detail_columns['PK'] = detail_pk_cols[0] if len(detail_pk_cols) == 1 else ','.join(detail_pk_cols)
                    print(f"   Mapping PK -> {detail_columns['PK']}")
                
                # Map COLNAME placeholder (Additional Context Columns)
                if 'COLNAME' in detail_placeholders and detail_context_cols:
                    detail_columns['COLNAME'] = detail_context_cols[0] if len(detail_context_cols) == 1 else ','.join(detail_context_cols)
                    print(f"   Mapping COLNAME -> {detail_columns['COLNAME']}")
                
                # Map remaining placeholders from the ratio metric (e.g., VAL_COL)
                for placeholder in detail_placeholders:
                    if placeholder not in ['PK', 'COLNAME'] and placeholder in input_columns:
                        detail_columns[placeholder] = input_columns[placeholder]
                        print(f"   Mapping {placeholder} -> {detail_columns[placeholder]}")
                
                # Save detail metric binding
                detail_success = db_utils.save_custom_metric(
                    schema=schema,
                    table=table,
                    metric_name=f"{metric_name}_details_json",
                    function_name=detail_template_name,
                    input_columns=detail_columns,
                    good_threshold=None,  # Detail metrics don't have thresholds
                    acceptable_threshold=None,
                    enabled=enabled
                )
                
                if not detail_success:
                    print(f"⚠️ Warning: Failed to save detail metric")
            else:
                print(f"⚠️ Detail template '{detail_template_name}' not found")
        
        if success:
            # Keep modal open, show success message, enable auto-refresh, and show toast
            toast = dbc.Toast(
                [html.I(className='fas fa-check-circle me-2'), "Added successfully!"],
                header="Success",
                icon="success",
                duration=4000,
                is_open=True,
                style={"position": "fixed", "top": 80, "right": 20, "width": 350, "zIndex": 9999}
            )
            return True, dbc.Alert([
                html.I(className='fas fa-check-circle me-2'),
                f'Custom metric "{metric_name}" added successfully!',
                html.Br(),
                html.Small('Page will refresh in 2 seconds...', className='text-muted')
            ], color='success'), False, toast  # Enable the interval (disabled=False) and show toast
        else:
            print("❌ Failed to save metric")
            return True, dbc.Alert("❌ Failed to save metric. Check logs for details.", color="danger"), True, html.Div()
        
    except Exception as e:
        print(f"❌ Error saving metric: {e}")
        import traceback
        traceback.print_exc()
        return False, html.Div()

# Show/hide fields based on profile type
@callback(
    [Output('timestamp-col-section', 'style'),
     Output('granularities-section', 'style')],
    Input('edit-profile-type', 'value'),
    prevent_initial_call=False
)
def toggle_profile_fields(profile_type):
    """Show/hide timestamp and granularities fields based on profile type"""
    print(f"🔄 Callback triggered with profile_type: '{profile_type}'")
    
    if profile_type == 'TimeSeries':
        # Show both fields for TimeSeries
        print("   → Showing TimeSeries fields")
        return {'display': 'block'}, {'display': 'block'}
    else:  # Snapshot
        # Hide both fields for Snapshot
        print("   → Hiding fields (Snapshot mode)")
        return {'display': 'none'}, {'display': 'none'}

# Show/hide schedule fields based on frequency and generate cron
@callback(
    [Output('hour-interval-section', 'style'),
     Output('day-of-week-section', 'style'),
     Output('day-of-month-section', 'style'),
     Output('edit-schedule-cron', 'data'),
     Output('cron-display', 'children')],
    [Input('schedule-frequency', 'value'),
     Input('schedule-hour-interval', 'value'),
     Input('schedule-day-of-week', 'value'),
     Input('schedule-day-of-month', 'value'),
     Input('schedule-hour', 'value'),
     Input('schedule-minute', 'value')],
    prevent_initial_call=False
)
def update_schedule(frequency, hour_interval, day_of_week, day_of_month, hour, minute):
    """Show/hide fields based on frequency and generate cron expression"""
    
    # Default: hide all optional fields
    show_hour_interval = {'display': 'none'}
    show_day_of_week = {'display': 'none'}
    show_day_of_month = {'display': 'none'}
    
    # Generate cron based on frequency
    # Cron format: second minute hour day month day-of-week
    
    if frequency == 'hour':
        # Every X hours at specified minute
        show_hour_interval = {'display': 'inline-block'}
        if hour_interval == '1':
            # Every hour
            cron = f"0 {minute} * * * ?"
        else:
            # Every X hours (e.g., */2, */4, */6)
            cron = f"0 {minute} */{hour_interval} * * ?"
        
    elif frequency == 'day':
        # Every day at specified time
        cron = f"0 {minute} {hour} * * ?"
        # Don't show day-of-week or day-of-month
        
    elif frequency == 'week':
        # Every week on specified day at specified time
        cron = f"0 {minute} {hour} ? * {day_of_week}"
        show_day_of_week = {'display': 'inline'}  # Show day of week
        
    elif frequency == 'month':
        # Every month on specified day at specified time
        cron = f"0 {minute} {hour} {day_of_month} * ?"
        show_day_of_month = {'display': 'inline'}  # Show day of month
    else:
        cron = "0 0 0 * * ?"
    
    return show_hour_interval, show_day_of_week, show_day_of_month, cron, cron

# Navigate to edit page when edit button is clicked
@callback(
    Output('url', 'pathname', allow_duplicate=True),
    Input('edit-monitor-btn', 'n_clicks'),
    State('monitors-table', 'selected_rows'),
    State('monitors-table', 'data'),
    prevent_initial_call=True
)
def navigate_to_edit(n_clicks, selected_rows, data):
    """Navigate to edit page for the selected monitor"""
    if not n_clicks or not selected_rows or not data:
        return '/config'
    
    import urllib.parse
    
    selected_row = data[selected_rows[0]]
    catalog = urllib.parse.quote(selected_row['Catalog'])
    schema = urllib.parse.quote(selected_row['Schema'])
    table = urllib.parse.quote(selected_row['Table'])
    
    return f'/config/edit/{catalog}/{schema}/{table}'

# Save changes from edit page
@callback(
    Output('edit-status', 'children'),
    Input('save-edit-btn', 'n_clicks'),
    State('edit-catalog', 'data'),
    State('edit-schema', 'data'),
    State('edit-table', 'data'),
    State('edit-profile-type', 'value'),
    State('edit-timestamp-col', 'value'),
    State('edit-granularities', 'value'),
    State('edit-schedule-cron', 'data'),
    State('edit-enabled', 'value'),
    prevent_initial_call=True
)
def save_edit(n_clicks, catalog, schema, table, profile_type, timestamp_col, 
              granularities, schedule_cron, enabled):
    """Save changes from edit form"""
    if not n_clicks:
        return ''
    
    try:
        # Build updates based on profile type
        updates = {
            'profile_type': profile_type,
            'schedule_cron': schedule_cron,  # Use the generated cron from the store
            'enabled': enabled
        }
        
        # Only include TimeSeries-specific fields if profile_type is TimeSeries
        if profile_type == 'TimeSeries':
            updates['timestamp_col'] = timestamp_col
            # Keep granularities as a list for proper array handling
            updates['granularities'] = granularities if isinstance(granularities, list) else []
        else:  # Snapshot
            # Set these to NULL for Snapshot profiles
            updates['timestamp_col'] = None
            updates['granularities'] = None
        
        success = db_utils.update_monitor_control(catalog, schema, table, updates)
        
        if success:
            return dbc.Alert([
                html.P("✅ Changes saved successfully!", className='mb-2'),
                dbc.Button("Back to Configuration", href="/config", color="success", size="sm")
            ], color="success")
        else:
            return dbc.Alert("❌ Failed to save changes. Check logs for details.", 
                           color="danger", dismissable=True)
        
    except Exception as e:
        print(f"❌ Error saving edit: {e}")
        import traceback
        traceback.print_exc()
        return dbc.Alert(f"❌ Error: {str(e)}", color="danger", dismissable=True)



# ========== DELETE CUSTOM METRIC CALLBACKS ==========

# Delete custom metric - just show confirmation modal
@callback(
    [Output('delete-confirmation-modal', 'is_open', allow_duplicate=True),
     Output('delete-metric-name', 'data', allow_duplicate=True),
     Output('delete-metric-name-display', 'children', allow_duplicate=True)],
    Input({'type': 'delete-metric', 'index': ALL}, 'n_clicks'),
    [State({'type': 'delete-metric', 'index': ALL}, 'id'),
     State('edit-schema', 'data'),
     State('edit-table', 'data')],
    prevent_initial_call=True
)
def delete_custom_metric_callback(n_clicks_list, button_ids, schema, table):
    """Handle delete button clicks for custom metrics"""
    print(f"🔍 DELETE CALLBACK TRIGGERED - n_clicks: {n_clicks_list}")
    
    if not any(n_clicks_list):
        return no_update, no_update, no_update
    
    # Find which button was clicked
    if not ctx.triggered:
        return no_update, no_update, no_update
    
    triggered_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    if not triggered_id:
        return no_update, no_update, no_update
    
    # Parse the triggered ID to get the metric name
    import json
    try:
        button_id = json.loads(triggered_id)
        metric_name = button_id['index']
    except:
        return no_update, no_update, no_update
    
    print(f"🗑️ Delete button clicked for metric: {metric_name}")
    
    # Show confirmation modal and store metric name
    print(f"   → Returning: True, '{metric_name}', '{metric_name}'")
    return True, metric_name, metric_name


# Confirm delete metric - with refresh trigger  
@callback(
    [Output('delete-confirmation-modal', 'is_open', allow_duplicate=True),
     Output('toast-container', 'children', allow_duplicate=True),
     Output('url', 'pathname', allow_duplicate=True),
     Output('url', 'search', allow_duplicate=True)],
    [Input('confirm-delete-metric', 'n_clicks'),
     Input('cancel-delete-metric', 'n_clicks')],
    [State('delete-metric-name', 'data'),
     State('edit-schema', 'data'),
     State('edit-table', 'data'),
     State('url', 'pathname')],
    prevent_initial_call=True
)
def confirm_delete_metric(confirm_clicks, cancel_clicks, metric_name, schema, table, current_pathname):
    """Handle delete confirmation"""
    print(f"🔍 CONFIRM DELETE CALLBACK TRIGGERED")
    
    if not ctx.triggered:
        return no_update, no_update, no_update, no_update
    
    triggered_id = ctx.triggered[0]['prop_id']
    
    if 'cancel-delete-metric' in triggered_id:
        # Cancel - just close modal
        return False, html.Div(), no_update, no_update  # Close modal, no toast, no refresh
    
    if 'confirm-delete-metric' in triggered_id and confirm_clicks:
        # Confirm delete
        print(f"🗑️ Confirming delete of metric: {metric_name}")
        
        # Delete from database
        success = db_utils.delete_custom_metric(schema, table, metric_name)
        
        if success:
            print(f"✅ Metric deleted successfully - triggering page reload")
            # Close modal and show toast
            toast = dbc.Toast(
                [html.I(className='fas fa-check-circle me-2'), "Deleted successfully! Refreshing..."],
                header="Success",
                icon="success",
                duration=2000,
                is_open=True,
                style={"position": "fixed", "top": 80, "right": 20, "width": 350, "zIndex": 9999}
            )
            # Force page reload by updating the search params with timestamp
            import time
            search_param = f"?_reload={int(time.time() * 1000)}"
            print(f"   Triggering reload: {current_pathname}{search_param}")
            return False, toast, current_pathname, search_param  # Close modal, show toast, trigger reload
        else:
            print(f"❌ Failed to delete metric")
            # Keep modal open to show error
            error_toast = dbc.Toast(
                [html.I(className='fas fa-times-circle me-2'), "Failed to delete metric!"],
                header="Error",
                icon="danger",
                duration=4000,
                is_open=True,
                style={"position": "fixed", "top": 80, "right": 20, "width": 350, "zIndex": 9999}
            )
            return True, error_toast, no_update, no_update  # Keep modal open, show error toast, no refresh
    
    return no_update, no_update, no_update, no_update


# Auto-refresh page after successful save using clientside callback for real page reload
dash_app.clientside_callback(
    """
    function(n_intervals) {
        if (n_intervals > 0) {
            console.log('🔄 Auto-refresh triggered after save, reloading page...');
            window.location.reload();
        }
        return window.dash_clientside.no_update;
    }
    """,
    Output('refresh-after-save-interval', 'disabled', allow_duplicate=True),
    Input('refresh-after-save-interval', 'n_intervals'),
    prevent_initial_call=True
)


# ========== REGISTER NEW TABLE CALLBACKS ==========

# Open register table modal
@callback(
    [Output('register-table-modal', 'is_open', allow_duplicate=True),
     Output('register-table-form-content', 'children', allow_duplicate=True)],
    [Input('register-new-table-btn', 'n_clicks'),
     Input('register-table-cancel', 'n_clicks')],
    State('register-table-modal', 'is_open'),
    prevent_initial_call=True
)
def toggle_register_table_modal(register_clicks, cancel_clicks, is_open):
    """Toggle the register table modal and load initial form"""
    if not ctx.triggered:
        return no_update, no_update
    
    triggered_id = ctx.triggered[0]['prop_id']
    
    if 'cancel' in triggered_id:
        return False, html.Div()
    
    if 'register-new-table-btn' in triggered_id and register_clicks:
        print("📝 Opening Register New Table modal")
        
        # Build initial form - Step 1: Select Table
        form_content = build_register_table_form_step1()
        return True, form_content
    
    return no_update, no_update

def build_register_table_form_step1():
    """Step 1: Select catalog, schema, and table"""
    try:
        # Fetch available catalogs - use system.information_schema to get all accessible catalogs
        catalogs_query = """
        SHOW CATALOGS
        """
        df_catalogs = db_utils.execute_query(catalogs_query)
        # Filter out system catalogs
        df_catalogs = df_catalogs[~df_catalogs['catalog'].isin(['system', '__databricks_internal'])]
        catalog_options = [{'label': cat, 'value': cat} for cat in df_catalogs['catalog'].tolist()]
        
        return html.Div([
            dbc.Alert([
                html.I(className='fas fa-info-circle me-2'),
                "Select a table to register for data quality monitoring."
            ], color='info'),
            
            dbc.Row([
                dbc.Label("Catalog", width=12, className='fw-bold'),
                dbc.Col([
                    dcc.Dropdown(
                        id='register-catalog-dropdown',
                        options=catalog_options,
                        placeholder="Select catalog..."
                    )
                ], width=12)
            ], className='mb-3'),
            
            dbc.Row([
                dbc.Label("Schema", width=12, className='fw-bold'),
                dbc.Col([
                    dcc.Dropdown(
                        id='register-schema-dropdown',
                        options=[],
                        placeholder="Select schema...",
                        disabled=True
                    )
                ], width=12)
            ], className='mb-3'),
            
            dbc.Row([
                dbc.Label("Table", width=12, className='fw-bold'),
                dbc.Col([
                    dcc.Dropdown(
                        id='register-table-dropdown',
                        options=[],
                        placeholder="Select table...",
                        disabled=True
                    )
                ], width=12)
            ], className='mb-3'),
            
            # Hidden divs to store selections and trigger next steps
            dcc.Store(id='register-selected-catalog', data=''),
            dcc.Store(id='register-selected-schema', data=''),
            dcc.Store(id='register-selected-table', data=''),
            
            html.Hr(),
            
            # Placeholder for table preview and configuration
            html.Div(id='register-table-preview-section')
        ])
        
    except Exception as e:
        print(f"❌ Error building register form step 1: {e}")
        import traceback
        traceback.print_exc()
        return dbc.Alert(f"Error loading form: {str(e)}", color="danger")

# Load schemas when catalog is selected
@callback(
    [Output('register-schema-dropdown', 'options'),
     Output('register-schema-dropdown', 'disabled'),
     Output('register-selected-catalog', 'data')],
    Input('register-catalog-dropdown', 'value'),
    prevent_initial_call=True
)
def load_schemas_for_register(catalog):
    """Load schemas for the selected catalog"""
    if not catalog:
        return [], True, ''
    
    try:
        schemas_query = f"""
        SELECT DISTINCT schema_name
        FROM {catalog}.information_schema.schemata
        WHERE schema_name NOT IN ('information_schema')
        ORDER BY schema_name
        """
        df_schemas = db_utils.execute_query(schemas_query)
        schema_options = [{'label': sch, 'value': sch} for sch in df_schemas['schema_name'].tolist()]
        return schema_options, False, catalog
    except Exception as e:
        print(f"❌ Error loading schemas: {e}")
        return [], True, ''

# Load tables when schema is selected
@callback(
    [Output('register-table-dropdown', 'options'),
     Output('register-table-dropdown', 'disabled'),
     Output('register-selected-schema', 'data')],
    [Input('register-schema-dropdown', 'value'),
     State('register-selected-catalog', 'data')],
    prevent_initial_call=True
)
def load_tables_for_register(schema, catalog):
    """Load tables for the selected schema"""
    print(f"\n📊 Loading tables for: catalog='{catalog}', schema='{schema}'")
    
    if not schema or not catalog:
        print(f"❌ Missing catalog or schema: catalog='{catalog}', schema='{schema}'")
        return [], True, ''
    
    try:
        # Use SHOW TABLES for more reliable results
        tables_query = f"""
        SHOW TABLES IN {catalog}.{schema}
        """
        print(f"📝 Query: {tables_query}")
        df_tables = db_utils.execute_query(tables_query)
        print(f"✅ Found {len(df_tables)} tables")
        
        # SHOW TABLES returns columns: database, tableName, isTemporary
        table_options = [{'label': tbl, 'value': tbl} for tbl in df_tables['tableName'].tolist()]
        print(f"✅ Table options: {table_options[:5]}...")  # Show first 5
        return table_options, False, schema
    except Exception as e:
        print(f"❌ Error loading tables: {e}")
        import traceback
        traceback.print_exc()
        return [], True, ''

# Show table preview and configuration when table is selected
@callback(
    [Output('register-table-preview-section', 'children'),
     Output('register-selected-table', 'data')],
    [Input('register-table-dropdown', 'value'),
     State('register-selected-catalog', 'data'),
     State('register-selected-schema', 'data')],
    prevent_initial_call=True
)
def show_register_table_preview(table, catalog, schema):
    """Show table preview and monitoring configuration form"""
    if not table or not catalog or not schema:
        return html.Div(), ''
    
    try:
        print(f"📊 Loading preview for {catalog}.{schema}.{table}")
        
        # Fetch table preview (10 rows)
        preview_query = f"SELECT * FROM {catalog}.{schema}.{table} LIMIT 10"
        df_preview = db_utils.execute_query(preview_query)
        
        # Fetch table columns with types
        columns_query = f"""
        SELECT column_name, data_type
        FROM {catalog}.information_schema.columns
        WHERE table_catalog = '{catalog}'
          AND table_schema = '{schema}'
          AND table_name = '{table}'
        ORDER BY ordinal_position
        """
        df_columns = db_utils.execute_query(columns_query)
        
        # Filter timestamp columns for TimeSeries profile
        timestamp_columns = df_columns[
            df_columns['data_type'].str.contains('TIMESTAMP|DATE', case=False, na=False)
        ]['column_name'].tolist()
        
        return html.Div([
            # Table Preview (collapsible)
            dbc.Card([
                dbc.CardHeader([
                    html.H5([
                        html.I(className='fas fa-table me-2'),
                        f'Table Preview: {catalog}.{schema}.{table}'
                    ], className='mb-0')
                ]),
                dbc.CardBody([
                    html.P(f"Showing first 10 rows ({len(df_preview)} fetched, {len(df_columns)} columns total)"),
                    dash_table.DataTable(
                        data=df_preview.to_dict('records'),
                        columns=[{"name": i, "id": i} for i in df_preview.columns],
                        style_table={'overflowX': 'auto'},
                        style_cell={'textAlign': 'left', 'padding': '8px', 'fontSize': '12px'},
                        style_header={'backgroundColor': '#f8f9fa', 'fontWeight': 'bold'},
                        page_size=10
                    )
                ])
            ], className='mb-4'),
            
            # Monitoring Configuration Form
            html.H5([html.I(className='fas fa-cogs me-2'), 'Monitoring Configuration'], className='mb-3'),
            
            dbc.Row([
                dbc.Label("Profile Type", width=12, className='fw-bold'),
                dbc.Col([
                    dcc.Dropdown(
                        id='register-profile-type',
                        options=[
                            {'label': 'TimeSeries - Track metrics over time', 'value': 'TimeSeries'},
                            {'label': 'Snapshot - One-time snapshot', 'value': 'Snapshot'}
                        ],
                        value='TimeSeries',
                        clearable=False
                    )
                ], width=12)
            ], className='mb-3'),
            
            # TimeSeries-specific fields (conditional)
            dbc.Collapse([
                dbc.Row([
                    dbc.Label("Timestamp Column", width=12, className='fw-bold'),
                    dbc.Col([
                        dcc.Dropdown(
                            id='register-timestamp-column',
                            options=[{'label': f"{col} ({df_columns[df_columns['column_name']==col]['data_type'].iloc[0]})", 
                                     'value': col} for col in timestamp_columns],
                            placeholder="Select timestamp column..."
                        )
                    ], width=12)
                ], className='mb-3'),
                
                dbc.Row([
                    dbc.Label("Granularities", width=12, className='fw-bold'),
                    dbc.Col([
                        dcc.Dropdown(
                            id='register-granularities',
                            options=[
                                {'label': '5 minutes', 'value': '5 minutes'},
                                {'label': '30 minutes', 'value': '30 minutes'},
                                {'label': '1 hour', 'value': '1 hour'},
                                {'label': '1 day', 'value': '1 day'},
                                {'label': '1 week', 'value': '1 week'},
                                {'label': '1 month', 'value': '1 month'}
                            ],
                            multi=True,
                            value=['1 day']
                        ),
                        dbc.FormText("Select one or more time granularities for aggregation")
                    ], width=12)
                ], className='mb-3'),
            ], id='register-timeseries-fields', is_open=True),
            
            # Schedule Configuration
            html.Hr(),
            html.H6([html.I(className='fas fa-clock me-2'), 'Schedule'], className='mb-3'),
            
            dbc.Row([
                dbc.Label("Frequency", width=12, className='fw-bold'),
                dbc.Col([
                    dcc.Dropdown(
                        id='register-schedule-frequency',
                        options=[
                            {'label': 'Hourly', 'value': 'Hour'},
                            {'label': 'Daily', 'value': 'Day'},
                            {'label': 'Weekly', 'value': 'Week'},
                            {'label': 'Monthly', 'value': 'Month'}
                        ],
                        value='Day',
                        clearable=False
                    )
                ], width=12)
            ], className='mb-3'),
            
            # Dynamic schedule options based on frequency
            html.Div(id='register-schedule-options'),
            
            # Status
            dbc.Row([
                dbc.Label("Status", width=12, className='fw-bold'),
                dbc.Col([
                    dbc.RadioItems(
                        id='register-status',
                        options=[
                            {'label': ' Enabled', 'value': True},
                            {'label': ' Disabled', 'value': False}
                        ],
                        value=True,
                        inline=True
                    )
                ], width=12)
            ], className='mb-3'),
            
        ]), table
        
    except Exception as e:
        print(f"❌ Error loading table preview: {e}")
        import traceback
        traceback.print_exc()
        return dbc.Alert(f"Error loading table: {str(e)}", color="danger"), ''

# Toggle TimeSeries fields based on profile type
@callback(
    Output('register-timeseries-fields', 'is_open'),
    Input('register-profile-type', 'value'),
    prevent_initial_call=True
)
def toggle_register_timeseries_fields(profile_type):
    """Show/hide TimeSeries-specific fields"""
    return profile_type == 'TimeSeries'

# Dynamic schedule options based on frequency
@callback(
    Output('register-schedule-options', 'children'),
    Input('register-schedule-frequency', 'value'),
    prevent_initial_call=True
)
def update_register_schedule_options(frequency):
    """Show relevant schedule options based on frequency"""
    if frequency == 'Hour':
        return dbc.Row([
            dbc.Label("Interval (hours)", width=12, className='fw-bold'),
            dbc.Col([
                dcc.Dropdown(
                    id='register-schedule-interval',
                    options=[
                        {'label': 'Every hour', 'value': 1},
                        {'label': 'Every 2 hours', 'value': 2},
                        {'label': 'Every 3 hours', 'value': 3},
                        {'label': 'Every 4 hours', 'value': 4},
                        {'label': 'Every 6 hours', 'value': 6},
                        {'label': 'Every 8 hours', 'value': 8},
                        {'label': 'Every 12 hours', 'value': 12}
                    ],
                    value=1,
                    clearable=False
                )
            ], width=12)
        ], className='mb-3')
    elif frequency == 'Day':
        return dbc.Row([
            dbc.Label("Time of Day", width=12, className='fw-bold'),
            dbc.Col([
                dcc.Dropdown(
                    id='register-schedule-hour',
                    options=[{'label': f'{i:02d}:00', 'value': i} for i in range(24)],
                    value=0,
                    clearable=False
                )
            ], width=12)
        ], className='mb-3')
    elif frequency == 'Week':
        return dbc.Row([
            dbc.Label("Day of Week", width=12, className='fw-bold'),
            dbc.Col([
                dcc.Dropdown(
                    id='register-schedule-day-of-week',
                    options=[
                        {'label': 'Monday', 'value': 1},
                        {'label': 'Tuesday', 'value': 2},
                        {'label': 'Wednesday', 'value': 3},
                        {'label': 'Thursday', 'value': 4},
                        {'label': 'Friday', 'value': 5},
                        {'label': 'Saturday', 'value': 6},
                        {'label': 'Sunday', 'value': 0}
                    ],
                    value=1,
                    clearable=False
                )
            ], width=12)
        ], className='mb-3')
    elif frequency == 'Month':
        return dbc.Row([
            dbc.Label("Day of Month", width=12, className='fw-bold'),
            dbc.Col([
                dcc.Dropdown(
                    id='register-schedule-day-of-month',
                    options=[{'label': f'Day {i}', 'value': i} for i in range(1, 32)],
                    value=1,
                    clearable=False
                )
            ], width=12)
        ], className='mb-3')
    
    return html.Div()

# Save registered table
@callback(
    [Output('register-table-modal', 'is_open', allow_duplicate=True),
     Output('register-table-status', 'children'),
     Output('toast-container', 'children', allow_duplicate=True),
     Output('url', 'pathname', allow_duplicate=True),
     Output('url', 'search', allow_duplicate=True)],
    Input('register-table-save', 'n_clicks'),
    [State('register-selected-catalog', 'data'),
     State('register-selected-schema', 'data'),
     State('register-selected-table', 'data'),
     State('register-profile-type', 'value'),
     State('register-timestamp-column', 'value'),
     State('register-granularities', 'value'),
     State('register-schedule-frequency', 'value'),
     State('register-status', 'value'),
     State('url', 'pathname')],
    prevent_initial_call=True
)
def save_registered_table(n_clicks, catalog, schema, table, profile_type, timestamp_col, 
                         granularities, schedule_freq, enabled, current_pathname):
    """Save the newly registered table to monitors_control"""
    if not n_clicks:
        return no_update, no_update, no_update, no_update, no_update
    
    if not catalog or not schema or not table:
        error_alert = dbc.Alert("Please select a table to register", color="danger")
        return True, error_alert, html.Div(), no_update, no_update
    
    try:
        print(f"\n💾 Registering new table: {catalog}.{schema}.{table}")
        print(f"   Profile Type: {profile_type}")
        print(f"   Timestamp Column: {timestamp_col}")
        print(f"   Granularities: {granularities}")
        print(f"   Schedule: {schedule_freq}")
        print(f"   Enabled: {enabled}")
        
        # Validate TimeSeries-specific fields
        if profile_type == 'TimeSeries':
            if not timestamp_col:
                error_alert = dbc.Alert("Timestamp column is required for TimeSeries profile", color="danger")
                return True, error_alert, html.Div(), no_update, no_update
            if not granularities:
                error_alert = dbc.Alert("At least one granularity is required for TimeSeries profile", color="danger")
                return True, error_alert, html.Div(), no_update, no_update
        
        # Build cron expression based on schedule
        cron_expr = build_cron_expression(schedule_freq)
        
        # Prepare granularities array (or NULL for Snapshot)
        if profile_type == 'TimeSeries' and granularities:
            granularities_str = "array('" + "', '".join(granularities) + "')"
        else:
            granularities_str = "NULL"
        
        # Insert into monitors_control
        insert_query = f"""
        INSERT INTO {CATALOG}.{ADMIN_SCHEMA}.monitors_control
        (table_catalog, table_schema, table_name, profile_type, timestamp_col, granularities, schedule_cron, enabled)
        VALUES (
            '{catalog}',
            '{schema}',
            '{table}',
            '{profile_type}',
            {'NULL' if not timestamp_col else f"'{timestamp_col}'"},
            {granularities_str},
            '{cron_expr}',
            {str(enabled).upper()}
        )
        """
        
        print(f"📝 Insert query: {insert_query}")
        
        connection = db_utils.get_connection(SQL_WAREHOUSE_HTTP_PATH)
        cursor = connection.cursor()
        cursor.execute(insert_query)
        connection.commit()
        
        print(f"✅ Table registered successfully")
        
        # Show success toast and reload
        toast = dbc.Toast(
            [html.I(className='fas fa-check-circle me-2'), f"Table {table} registered successfully! Refreshing..."],
            header="Success",
            icon="success",
            duration=2000,
            is_open=True,
            style={"position": "fixed", "top": 80, "right": 20, "width": 350, "zIndex": 9999}
        )
        
        # Trigger reload
        import time
        search_param = f"?_reload={int(time.time() * 1000)}"
        
        return False, html.Div(), toast, current_pathname, search_param
        
    except Exception as e:
        print(f"❌ Error registering table: {e}")
        import traceback
        traceback.print_exc()
        
        error_alert = dbc.Alert(f"Error: {str(e)}", color="danger")
        return True, error_alert, html.Div(), no_update, no_update

def build_cron_expression(frequency):
    """Build a cron expression based on frequency
    
    Returns a simple cron expression for the given frequency.
    For more complex schedules, this would need to take additional parameters.
    """
    if frequency == 'Hour':
        return '0 * * * *'  # Every hour
    elif frequency == 'Day':
        return '0 0 * * *'  # Daily at midnight
    elif frequency == 'Week':
        return '0 0 * * 1'  # Weekly on Monday
    elif frequency == 'Month':
        return '0 0 1 * *'  # Monthly on the 1st
    else:
        return '0 0 * * *'  # Default to daily


# Note: Auto-refresh after delete is now handled by inline script in the toast
# (See confirm_delete_metric callback above)


if __name__ == '__main__':
    import os
    dash_app.run(
        debug=os.getenv('DEBUG', 'False').lower() == 'true',
        host='0.0.0.0',
        port=int(os.getenv('PORT', '8080'))
    )
