"""
Overview Page - Entry point showing monitored tables and metrics summary
"""

from dash import html, dcc, callback, Input, Output, State
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.db_helper import (
    get_monitored_tables,
    get_metric_templates,
    get_metric_bindings,
    get_table_metrics_summary,
    get_metrics_by_dimension
)

def create_stat_card(icon, value, label, color="primary"):
    """Create a statistics card"""
    return dbc.Card([
        dbc.CardBody([
            html.Div([
                html.I(className=f"fas {icon} fa-2x", style={"color": f"var(--bs-{color})"}),
                html.Div([
                    html.H3(value, className="mb-0", style={"fontWeight": "bold"}),
                    html.P(label, className="text-muted mb-0", style={"fontSize": "0.9rem"})
                ], className="ms-3")
            ], className="d-flex align-items-center")
        ])
    ], className="shadow-sm mb-3")


def create_table_card(row):
    """Create a card for each monitored table"""
    table_fqn = f"{row['table_schema']}.{row['table_name']}"
    
    # Status badge
    status_badge = dbc.Badge(
        "Active" if row['monitor_enabled'] else "Disabled",
        color="success" if row['monitor_enabled'] else "secondary",
        className="me-2"
    )
    
    # Metrics info
    metrics_info = f"{row['active_metrics']}/{row['total_metrics']} metrics active"
    
    # Dimensions covered
    dimensions = eval(row['dimensions_covered']) if row['dimensions_covered'] else []
    dimension_badges = [
        dbc.Badge(dim, color="info", className="me-1") 
        for dim in dimensions if dim
    ]
    
    return dbc.Card([
        dbc.CardHeader([
            html.Div([
                html.H5([
                    html.I(className="fas fa-table me-2"),
                    table_fqn
                ], className="mb-0"),
                status_badge
            ], className="d-flex justify-content-between align-items-center")
        ]),
        dbc.CardBody([
            html.Div([
                html.I(className="fas fa-chart-line me-2", style={"color": "#6c757d"}),
                html.Span(metrics_info, className="text-muted")
            ], className="mb-2"),
            html.Div([
                html.I(className="fas fa-shield-alt me-2", style={"color": "#6c757d"}),
                html.Span("DQ Dimensions: ", className="text-muted me-2"),
                html.Div(dimension_badges if dimension_badges else html.Span("None configured", className="text-muted"))
            ], className="mb-2"),
        ])
    ], className="shadow-sm mb-3")


def create_dimension_chart(df_dimensions):
    """Create a donut chart showing metrics by dimension"""
    if df_dimensions.empty:
        return go.Figure()
    
    colors = {
        'COMPLETENESS': '#0d6efd',
        'VALIDITY': '#198754',
        'CONSISTENCY': '#ffc107',
        'ACCURACY': '#dc3545',
        'N/A': '#6c757d'
    }
    
    fig = go.Figure(data=[go.Pie(
        labels=df_dimensions['dimension'],
        values=df_dimensions['template_count'],
        hole=.4,
        marker_colors=[colors.get(dim, '#6c757d') for dim in df_dimensions['dimension']]
    )])
    
    fig.update_layout(
        title_text="Metric Templates by DQ Dimension",
        showlegend=True,
        height=300,
        margin=dict(l=20, r=20, t=40, b=20)
    )
    
    return fig


# Layout
layout = html.Div([
    # Header
    dbc.Row([
        dbc.Col([
            html.H2([
                html.I(className="fas fa-home me-3"),
                "Data Quality Monitoring Overview"
            ]),
            html.P(
                "View and manage monitored tables, metric templates, and custom data quality rules.",
                className="text-muted"
            )
        ])
    ], className="mb-4"),
    
    # Statistics Cards
    dbc.Row([
        dbc.Col([
            html.Div(id="stats-tables-monitored")
        ], width=3),
        dbc.Col([
            html.Div(id="stats-total-metrics")
        ], width=3),
        dbc.Col([
            html.Div(id="stats-active-metrics")
        ], width=3),
        dbc.Col([
            html.Div(id="stats-templates")
        ], width=3),
    ], className="mb-4"),
    
    # Quick Actions
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader(html.H5("Quick Actions", className="mb-0")),
                dbc.CardBody([
                    dbc.Button([
                        html.I(className="fas fa-plus me-2"),
                        "Register New Table"
                    ], color="primary", href="/register-table", className="me-2 mb-2"),
                    dbc.Button([
                        html.I(className="fas fa-code me-2"),
                        "Create Metric Template"
                    ], color="success", href="/templates", className="me-2 mb-2"),
                    dbc.Button([
                        html.I(className="fas fa-link me-2"),
                        "Bind Metrics to Table"
                    ], color="info", href="/bind-metrics", className="mb-2"),
                ])
            ], className="shadow-sm")
        ])
    ], className="mb-4"),
    
    # Main Content - Two columns
    dbc.Row([
        # Left column - Monitored Tables
        dbc.Col([
            dbc.Card([
                dbc.CardHeader([
                    html.Div([
                        html.H5([
                            html.I(className="fas fa-database me-2"),
                            "Monitored Tables"
                        ], className="mb-0"),
                        dbc.Button([
                            html.I(className="fas fa-sync-alt me-2"),
                            "Refresh"
                        ], id="btn-refresh", color="secondary", size="sm", outline=True)
                    ], className="d-flex justify-content-between align-items-center")
                ]),
                dbc.CardBody([
                    dbc.Spinner(
                        html.Div(id="monitored-tables-list"),
                        color="primary"
                    )
                ])
            ], className="shadow-sm")
        ], width=8),
        
        # Right column - Metrics Info
        dbc.Col([
            # Dimension Distribution Chart
            dbc.Card([
                dbc.CardHeader(html.H5([
                    html.I(className="fas fa-chart-pie me-2"),
                    "Metric Templates"
                ], className="mb-0")),
                dbc.CardBody([
                    dbc.Spinner(
                        dcc.Graph(id="dimension-chart", config={'displayModeBar': False}),
                        color="primary"
                    )
                ])
            ], className="shadow-sm mb-3"),
            
            # Template Library Summary
            dbc.Card([
                dbc.CardHeader(html.H5([
                    html.I(className="fas fa-book me-2"),
                    "Template Library"
                ], className="mb-0")),
                dbc.CardBody([
                    html.Div(id="template-summary")
                ])
            ], className="shadow-sm")
        ], width=4)
    ]),
    
    # Hidden interval for auto-refresh (optional)
    dcc.Interval(id='interval-component', interval=60*1000, n_intervals=0, disabled=True)
])


# Callbacks
@callback(
    [Output('stats-tables-monitored', 'children'),
     Output('stats-total-metrics', 'children'),
     Output('stats-active-metrics', 'children'),
     Output('stats-templates', 'children'),
     Output('monitored-tables-list', 'children'),
     Output('dimension-chart', 'figure'),
     Output('template-summary', 'children')],
    [Input('btn-refresh', 'n_clicks'),
     Input('interval-component', 'n_intervals')]
)
def update_overview(n_clicks, n_intervals):
    """Update all overview components"""
    
    # Fetch data
    df_summary = get_table_metrics_summary()
    df_templates = get_metric_templates()
    df_dimensions = get_metrics_by_dimension()
    
    # Calculate statistics
    total_tables = len(df_summary)
    total_metrics = df_summary['total_metrics'].sum() if not df_summary.empty else 0
    active_metrics = df_summary['active_metrics'].sum() if not df_summary.empty else 0
    total_templates = len(df_templates)
    
    # Create stat cards
    stat_tables = create_stat_card("fa-database", str(total_tables), "Tables Monitored", "primary")
    stat_total_metrics = create_stat_card("fa-chart-line", str(total_metrics), "Total Metrics", "info")
    stat_active_metrics = create_stat_card("fa-check-circle", str(active_metrics), "Active Metrics", "success")
    stat_templates = create_stat_card("fa-code", str(total_templates), "Metric Templates", "warning")
    
    # Create table cards
    if df_summary.empty:
        table_cards = dbc.Alert([
            html.I(className="fas fa-info-circle me-2"),
            "No tables are currently being monitored. Click 'Register New Table' to get started."
        ], color="info")
    else:
        table_cards = [create_table_card(row) for _, row in df_summary.iterrows()]
    
    # Create dimension chart
    dimension_chart = create_dimension_chart(df_dimensions)
    
    # Create template summary
    if df_templates.empty:
        template_summary = dbc.Alert("No metric templates defined yet.", color="warning")
    else:
        template_groups = df_templates.groupby('dimension').size().reset_index(name='count')
        template_summary = html.Div([
            html.Div([
                dbc.Badge(
                    row['dimension'] if row['dimension'] else "N/A",
                    color="info",
                    className="me-2"
                ),
                html.Span(f"{row['count']} templates", className="text-muted")
            ], className="mb-2") for _, row in template_groups.iterrows()
        ])
    
    return (
        stat_tables,
        stat_total_metrics,
        stat_active_metrics,
        stat_templates,
        table_cards,
        dimension_chart,
        template_summary
    )

