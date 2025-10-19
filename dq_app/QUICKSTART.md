# Quick Start Guide

## 🎯 Overview

You now have a Data Quality Self-Service Portal with:

✅ **Entry Page (Overview)** - Fully functional
- Displays all monitored tables from `monitors_control`
- Shows metric counts and DQ dimensions from `metric_bindings` and `metric_templates`
- Live statistics and visualization
- Quick action buttons

✅ **Dashboard Page** - Placeholder for your existing DQ dashboard
✅ **Workflow Pages** - Placeholder pages for future enhancements

## 📁 Project Structure

```
dq_app/
├── app.py                      # Main Dash application
├── requirements.txt            # Python dependencies
├── databricks.yml             # Databricks App configuration
├── env.example                # Environment variables template
├── start.sh                   # Quick start script
├── README.md                  # Full documentation
├── pages/
│   ├── overview.py            # ✅ Entry page (COMPLETE)
│   ├── dashboard.py           # Placeholder for your dashboard
│   ├── register_table.py      # Placeholder for table registration
│   ├── templates.py           # Placeholder for template management
│   └── bind_metrics.py        # Placeholder for metric binding
└── utils/
    └── db_helper.py           # Database query functions
```

## 🚀 Getting Started

### Step 1: Configure Environment

```bash
cd /Users/steven.tan/Desktop/lakehouse_monitoring/dq_app

# Copy example environment file
cp env.example .env

# Edit with your Databricks credentials
nano .env  # or use your favorite editor
```

Required environment variables in `.env`:
```
DATABRICKS_SERVER_HOSTNAME=your-workspace.cloud.databricks.com
DATABRICKS_HTTP_PATH=/sql/1.0/warehouses/your-warehouse-id
DATABRICKS_TOKEN=dapi...

CATALOG=dbdemos_steventan
ADMIN_SCHEMA=monitoring_admin
DATA_SCHEMA=lakehouse_monitoring
OUT_SCHEMA=lakehouse_monitoring_demo_results
```

### Step 2: Install Dependencies

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install packages
pip install -r requirements.txt
```

### Step 3: Run the App

**Option A: Using the start script**
```bash
./start.sh
```

**Option B: Direct Python**
```bash
python app.py
```

The app will start on `http://localhost:8080`

## 📊 What the Entry Page Shows

The Overview page queries the 3 metadata tables and displays:

### Statistics Cards
- **Tables Monitored** - Count from `monitors_control`
- **Total Metrics** - Sum of all metrics from `metric_bindings`
- **Active Metrics** - Count of enabled metrics
- **Metric Templates** - Count from `metric_templates`

### Monitored Tables List
For each table in `monitors_control`, shows:
- Table fully qualified name (schema.table)
- Status badge (Active/Disabled)
- Metrics count (active/total)
- DQ dimensions covered (COMPLETENESS, VALIDITY, etc.)

### Metric Templates Chart
- Donut chart showing template distribution by DQ dimension
- Color-coded by dimension type

### Template Library Summary
- Grouped list of templates by dimension
- Count per dimension category

## 🔄 How Data Flows

```
Entry Page (overview.py)
    ↓
utils/db_helper.py (query functions)
    ↓
SQL queries to metadata tables:
  • monitors_control
  • metric_templates  
  • metric_bindings
    ↓
Display results in UI components
```

## 📝 SQL Queries Used

The app runs these queries on page load:

1. **get_table_metrics_summary()** - Joins all 3 metadata tables:
   ```sql
   SELECT mc.*, COUNT(mb.metric_name), SUM(...), COLLECT_SET(mt.dimension)
   FROM monitors_control mc
   LEFT JOIN metric_bindings mb ON ...
   LEFT JOIN metric_templates mt ON ...
   ```

2. **get_metrics_by_dimension()** - Template counts:
   ```sql
   SELECT dimension, COUNT(*) FROM metric_templates
   GROUP BY dimension
   ```

## 🎨 Customization

### Change Color Theme
Edit `app.py` line 12:
```python
external_stylesheets=[dbc.themes.BOOTSTRAP, ...]
# Try: DARKLY, SOLAR, SLATE, CYBORG, etc.
```

### Add Your Dashboard
Edit `pages/dashboard.py` to embed your existing dashboard:
```python
# Option 1: Iframe
html.Iframe(src="https://your-dashboard-url", style={"width": "100%", "height": "800px"})

# Option 2: Direct integration
# Import and render your dashboard components
```

### Modify Catalog/Schema Names
Edit `.env` file or change defaults in:
- `app.py` (lines 17-20)
- `utils/db_helper.py` (lines 9-12)

## 🐛 Troubleshooting

**Error: "Could not connect to Databricks"**
- Check `.env` file credentials
- Verify SQL Warehouse is running
- Test connection manually

**Error: "Table not found"**
- Verify metadata tables exist in your catalog
- Check catalog/schema names in `.env`
- Run the lakehouse_monitoring setup notebooks first

**Page shows "No tables monitored"**
- Metadata tables are empty
- Run notebooks to populate:
  - `02_metadata_tables.ipynb`
  - `05_additional_metadata_tables.ipynb`

## 🔜 Next Steps

1. **Test the Entry Page** - Verify it displays your monitored tables
2. **Embed Your Dashboard** - Add iframe/integration to dashboard page
3. **Build Workflows** - Complete the placeholder pages:
   - `register_table.py` - Add table registration form
   - `templates.py` - Add template creation wizard
   - `bind_metrics.py` - Add metric binding interface

## 📚 References

- Full documentation: `README.md`
- Lakehouse Monitoring framework: `/notebooks/` directory
- Metadata table schemas: `02_metadata_tables.ipynb`, `05_additional_metadata_tables.ipynb`

---

**🎉 You're ready to go!** Start the app and view your data quality monitoring overview.

