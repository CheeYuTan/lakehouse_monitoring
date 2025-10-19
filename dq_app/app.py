"""
Data Quality Self-Service Portal - Databricks App
Main application entry point
"""

import dash
from dash import html, dcc, callback, Input, Output
import dash_bootstrap_components as dbc
from databricks import sql
import os

# Initialize Dash app with Bootstrap theme
app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.BOOTSTRAP, dbc.icons.FONT_AWESOME],
    suppress_callback_exceptions=True
)

server = app.server

# Configuration - Update these based on your environment
CATALOG = os.getenv("CATALOG", "dbdemos_steventan")
ADMIN_SCHEMA = os.getenv("ADMIN_SCHEMA", "monitoring_admin")
DATA_SCHEMA = os.getenv("DATA_SCHEMA", "lakehouse_monitoring")
OUT_SCHEMA = os.getenv("OUT_SCHEMA", "lakehouse_monitoring_demo_results")

# Databricks SQL connection
def get_databricks_connection():
    """Create connection to Databricks SQL Warehouse"""
    return sql.connect(
        server_hostname=os.getenv("DATABRICKS_SERVER_HOSTNAME"),
        http_path=os.getenv("DATABRICKS_HTTP_PATH"),
        access_token=os.getenv("DATABRICKS_TOKEN")
    )

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
                dbc.NavItem(dbc.NavLink("Overview", href="/", active="exact")),
                dbc.NavItem(dbc.NavLink("Dashboard", href="/dashboard", active="exact")),
                dbc.NavItem(dbc.NavLink("Register Table", href="/register-table", active="exact")),
                dbc.NavItem(dbc.NavLink("Metric Templates", href="/templates", active="exact")),
                dbc.NavItem(dbc.NavLink("Bind Metrics", href="/bind-metrics", active="exact")),
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
app.layout = html.Div([
    dcc.Location(id='url', refresh=False),
    navbar,
    dbc.Container(id='page-content', fluid=True)
])

# Import page layouts
from pages import overview, dashboard, register_table, templates, bind_metrics

# Router callback
@callback(
    Output('page-content', 'children'),
    Input('url', 'pathname')
)
def display_page(pathname):
    if pathname == '/dashboard':
        return dashboard.layout
    elif pathname == '/register-table':
        return register_table.layout
    elif pathname == '/templates':
        return templates.layout
    elif pathname == '/bind-metrics':
        return bind_metrics.layout
    else:  # Default to overview
        return overview.layout

if __name__ == '__main__':
    app.run_server(debug=True, host='0.0.0.0', port=8080)

