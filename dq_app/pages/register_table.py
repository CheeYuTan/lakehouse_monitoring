"""
Register Table Page - Workflow for adding new tables to monitoring
"""

from dash import html
import dash_bootstrap_components as dbc

layout = html.Div([
    dbc.Row([
        dbc.Col([
            html.H2([
                html.I(className="fas fa-plus-circle me-3"),
                "Register Table for Monitoring"
            ]),
            html.P(
                "Add a new table to the Data Quality monitoring framework.",
                className="text-muted"
            )
        ])
    ], className="mb-4"),
    
    dbc.Alert([
        html.H4("Coming Soon", className="alert-heading"),
        html.P("This workflow will allow you to:"),
        html.Ul([
            html.Li("Select a table from your catalog"),
            html.Li("Configure profiling settings (timestamp column, granularities)"),
            html.Li("Set output locations and scheduling"),
            html.Li("Preview and register the monitor")
        ]),
    ], color="warning")
])

