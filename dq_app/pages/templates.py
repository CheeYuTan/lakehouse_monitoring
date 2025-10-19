"""
Metric Templates Page - Browse and create metric templates
"""

from dash import html
import dash_bootstrap_components as dbc

layout = html.Div([
    dbc.Row([
        dbc.Col([
            html.H2([
                html.I(className="fas fa-code me-3"),
                "Metric Template Library"
            ]),
            html.P(
                "Browse existing templates and create new custom data quality metrics.",
                className="text-muted"
            )
        ])
    ], className="mb-4"),
    
    dbc.Alert([
        html.H4("Coming Soon", className="alert-heading"),
        html.P("This page will allow you to:"),
        html.Ul([
            html.Li("Browse all metric templates by dimension"),
            html.Li("Create new metric templates with SQL expressions"),
            html.Li("Configure thresholds and parameters"),
            html.Li("Auto-generate details companion metrics")
        ]),
    ], color="warning")
])

