# Data Quality Self-Service Portal

A Databricks App for data quality stewards to manage Lakehouse Monitoring through a self-service interface.

## Features

- **Overview Dashboard**: View all monitored tables and metrics at a glance
- **Register Tables**: Add new tables to monitoring with guided workflow
- **Metric Templates**: Create and manage reusable data quality rules
- **Bind Metrics**: Attach metrics to tables with parameter configuration
- **Integrated Dashboard**: View your existing DQ dashboard

## Architecture

This app provides a user-friendly interface to the metadata-driven Lakehouse Monitoring framework:

```
┌─────────────────────────────────────────────────────────┐
│                    Dash Web App                          │
│  (Self-Service Portal for DQ Stewards)                  │
└─────────────────┬───────────────────────────────────────┘
                  │
                  ↓
┌─────────────────────────────────────────────────────────┐
│              Metadata Tables                             │
│  • monitors_control    (what to monitor)                │
│  • metric_templates    (how to monitor)                 │
│  • metric_bindings     (which metrics per table)        │
└─────────────────┬───────────────────────────────────────┘
                  │
                  ↓
┌─────────────────────────────────────────────────────────┐
│         Lakehouse Monitoring API                         │
│  (Automated monitor creation and execution)             │
└─────────────────────────────────────────────────────────┘
```

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

Copy `env.example` to `.env` and update with your Databricks credentials:

```bash
cp env.example .env
```

Edit `.env`:
```
DATABRICKS_SERVER_HOSTNAME=your-workspace.cloud.databricks.com
DATABRICKS_HTTP_PATH=/sql/1.0/warehouses/your-warehouse-id
DATABRICKS_TOKEN=dapi...
```

### 3. Run Locally

```bash
chmod +x start.sh
./start.sh
```

Or directly:
```bash
python app.py
```

The app will be available at `http://localhost:8080`

### 4. Deploy to Databricks

```bash
databricks apps create dq_portal
databricks apps deploy dq_portal
```

## Project Structure

```
dq_app/
├── app.py                  # Main application entry point
├── requirements.txt        # Python dependencies
├── databricks.yml         # Databricks App configuration
├── pages/                 # Page modules
│   ├── __init__.py
│   ├── overview.py        # Entry page (overview)
│   ├── dashboard.py       # DQ dashboard integration
│   ├── register_table.py  # Register new tables
│   ├── templates.py       # Metric template management
│   └── bind_metrics.py    # Bind metrics to tables
└── utils/                 # Helper modules
    ├── __init__.py
    └── db_helper.py       # Database query functions
```

## Usage

### Overview Page

The landing page shows:
- Statistics: tables monitored, total/active metrics, templates
- List of monitored tables with their metrics and dimensions
- Metric template distribution by DQ dimension
- Quick action buttons to start workflows

### Workflows

1. **Register Table**: Add a new table to monitoring
   - Select catalog/schema/table
   - Configure profiling (timestamp, granularity)
   - Set schedule and output location

2. **Create Metric Template**: Define reusable DQ rules
   - Choose dimension (COMPLETENESS, VALIDITY, etc.)
   - Write SQL expression with parameters
   - Set thresholds

3. **Bind Metrics**: Attach metrics to tables
   - Select table
   - Choose metrics
   - Configure column mappings

## Data Quality Dimensions

The framework organizes metrics into four dimensions:

- **COMPLETENESS**: Missing values, NULL checks
- **VALIDITY**: Format validation, range checks, negative values
- **CONSISTENCY**: Cross-field validation, referential integrity
- **ACCURACY**: Business rule validation, out-of-range detection

## Metadata Tables

### monitors_control
Defines which tables are monitored and how:
- Table identity (catalog, schema, name)
- Profiling configuration (timestamp, granularity)
- Output location and scheduling

### metric_templates
Reusable metric definitions:
- Template name and description
- SQL expression with parameters
- DQ dimension and thresholds

### metric_bindings
Links templates to specific tables:
- Table reference
- Template reference
- Parameter values (column names, etc.)

## Development

The app uses:
- **Dash** + **Dash Bootstrap Components** for UI
- **Plotly** for visualizations
- **Databricks SQL Connector** for queries
- **Pandas** for data processing

## Next Steps

- Complete workflow pages (register, templates, bind)
- Add validation and error handling
- Implement preview/test functionality
- Add audit logging
- Enable bulk operations

