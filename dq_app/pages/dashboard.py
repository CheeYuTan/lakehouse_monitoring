"""
Dashboard Page - Placeholder for existing DQ dashboard
"""

from dash import html
import dash_bootstrap_components as dbc

layout = html.Div([
    dbc.Row([
        dbc.Col([
            html.H2([
                html.I(className="fas fa-chart-bar me-3"),
                "Data Quality Dashboard"
            ]),
            html.P(
                "Embed your existing DQ dashboard here.",
                className="text-muted"
            )
        ])
    ], className="mb-4"),
    
    dbc.Alert([
        html.H4("Dashboard Integration", className="alert-heading"),
        html.P("This page will display your existing Data Quality dashboard."),
        html.Hr(),
        html.P("You can embed it using iframe or integrate directly with dashboard APIs.", className="mb-0")
    ], color="info")
])

