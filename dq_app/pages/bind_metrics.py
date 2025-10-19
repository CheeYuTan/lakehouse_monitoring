"""
Bind Metrics Page - Attach metrics to tables
"""

from dash import html
import dash_bootstrap_components as dbc

layout = html.Div([
    dbc.Row([
        dbc.Col([
            html.H2([
                html.I(className="fas fa-link me-3"),
                "Bind Metrics to Tables"
            ]),
            html.P(
                "Attach metric templates to monitored tables with specific parameters.",
                className="text-muted"
            )
        ])
    ], className="mb-4"),
    
    dbc.Alert([
        html.H4("Coming Soon", className="alert-heading"),
        html.P("This page will allow you to:"),
        html.Ul([
            html.Li("Select a monitored table"),
            html.Li("Choose metrics from template library"),
            html.Li("Configure column mappings and parameters"),
            html.Li("Preview and apply bindings")
        ]),
    ], color="warning")
])

