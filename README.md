# 🧠 Lakehouse Monitoring on Databricks

**Version:** v0.4 — *Self-Service Data Quality Portal*

This release builds upon v0.3 by adding a **self-service web portal** — a Databricks App that provides a user-friendly interface for managing the entire data quality monitoring framework.

Instead of working directly with notebooks and SQL, v0.4 introduces a Dash-based web application where data quality stewards can:
- View real-time data quality dashboards
- Register new tables for monitoring
- Create and manage custom DQ metrics
- Browse available DQ functions
- Configure monitoring schedules

The portal provides a seamless experience for non-technical users while maintaining the metadata-driven architecture from previous versions.

---

## 📚 What's Included

| Notebook | Description |
|-----------|-------------|
| `01_generate_sample_data.ipynb` | Generates sample data tables for testing (`policies`, `claims`, `premium_billing`). |
| `02_metadata_table.ipynb` | Sets up the foundational `monitors_control` metadata table. |
| `04_lakehouse_monitoring_functions.ipynb` | Defines reusable SQL functions grouped by DQ dimensions (Validity, Completeness, Consistency, Accuracy). |
| `05_additional_metadata_tables.ipynb` | Creates the `metric_templates` and `metric_bindings` metadata tables. |
| `06_lakehouse_monitoring_API_v0.2.ipynb` | Registers Lakehouse Monitors using all metadata tables. |
| `07_results_view_creation.ipynb` | Builds three dynamic, consolidated views (`dq_all_metrics`, `dq_all_metric_details`, `dq_all_metrics_default_profile`) for downstream visualization. |
| `08_dashboard_template_rewriter.ipynb` | Utility notebook to adapt dashboard templates dynamically (replacing catalog/schema/view references). |

| Application | Description |
|-------------|-------------|
| `dq_app/` | **Self-Service DQ Portal** — Databricks App for managing monitoring configuration, viewing dashboards, and creating custom metrics. |

---

## ⚙️ Architecture Overview

### From Metrics to Monitoring
```
SQL Functions → Metric Templates → Metric Bindings → Monitors Control → Lakehouse Monitoring API
```

### v0.3 — Results Aggregation Layer
```
Monitoring Results → dq_all_metrics / dq_all_metric_details / dq_all_metrics_default_profile → Dashboards
```

### v0.4 — Self-Service Portal Layer
```
Web Portal (Databricks App) → Metadata Tables → Monitoring Pipeline → Unified Views → Dashboards
```

The entire end-to-end pipeline now looks like this:
```
Self-Service Portal → Metadata Tables + API Automation → Monitors → Profile & Custom Metrics → Unified Views → DQ Dashboard
```

This allows data quality stewards to manage the entire monitoring lifecycle through an intuitive web interface, while the framework automatically updates dashboards as new monitors are created.

---

## 📊 Unified Views

| View | Description |
|------|--------------|
| **`dq_all_metrics`** | Aggregated results of all ratio metrics (e.g., missing values, negative amounts, out-of-range checks) with thresholds and DQ dimensions. |
| **`dq_all_metric_details`** | JSON-exploded details of offending rows, including primary key, values, and reasons — perfect for investigation or drill-down dashboards. |
| **`dq_all_metrics_default_profile`** | Unified baseline statistics (mean, nulls, distincts, etc.) across all monitored tables for comparison and health trends. |

These views can directly power a **Data Quality Scorecard** in Databricks SQL or BI tools such as Power BI, Tableau, or Looker.

---

## 🚀 How to Run

### Step 1: Setup Monitoring Framework

1. Execute all setup notebooks sequentially:
   ```
   01_generate_sample_data
   02_metadata_table
   04_lakehouse_monitoring_functions
   05_additional_metadata_tables
   06_lakehouse_monitoring_API_v0.2
   07_results_view_creation
   08_dashboard_template_rewriter
   ```

2. Inspect the generated views:
   ```sql
   SELECT * FROM dbdemos_steventan.lakehouse_monitoring_demo_results.dq_all_metrics;
   SELECT * FROM dbdemos_steventan.lakehouse_monitoring_demo_results.dq_all_metric_details;
   SELECT * FROM dbdemos_steventan.lakehouse_monitoring_demo_results.dq_all_metrics_default_profile;
   ```

3. (Optional) Use `Data Quality Dashboards Template.lvdash.json` under `/dashboards/` to render a unified visualization layer.

### Step 2: Deploy Self-Service Portal (NEW in v0.4)

1. **Configure the Portal**

   Edit `dq_app/app.yaml`:
   ```yaml
   env:
     - name: CATALOG
       value: "your_catalog_name"
     - name: ADMIN_SCHEMA
       value: "monitoring_admin"
     - name: SQL_WAREHOUSE_ID
       value: "your-warehouse-id"
     - name: DATABRICKS_ORG_ID
       value: "your-org-id"
     - name: DASHBOARD_ID
       value: "your-dashboard-id"
   ```

2. **Enable Dashboard Embedding**

   ⚠️ **Important Prerequisites:**
   - Dashboard must be **published** before embedding
   - Enable **"Embed dashboards"** in workspace settings:
     - Go to **Settings → Workspace admin → Security**
     - Under **External access**, set **"Embed dashboards"** to **"Allow"**

3. **Deploy the App**

   ```bash
   cd lakehouse_monitoring/dq_app

   databricks apps deploy <your-app-name> \
     --profile <your-profile> \
     --source-code-path /Workspace/Users/<your-user>/lakehouse_monitoring/dq_app
   ```

4. **Access the Portal**

   - Navigate to **Apps** in Databricks UI
   - Click on your app name
   - The portal opens with the Dashboard as the landing page

---

## 🧠 Design Highlights

### Framework Core
- **Dynamic Metadata Joins:** Views are automatically assembled from metadata and monitor outputs — no static references.  
- **Cross-Table Aggregation:** Combines multiple monitor outputs into a single consistent schema.  
- **Extensible Structure:** New metrics and monitors automatically appear in dashboards.  
- **Zero Manual Overhead:** No code edits needed when new tables are onboarded.

### Self-Service Portal (v0.4)
- **OAuth Authentication:** Secure, token-free authentication using Databricks service principals
- **Real-Time Dashboards:** Embedded Databricks dashboards showing latest DQ metrics
- **Table Registration:** Point-and-click interface to add tables to monitoring
- **Custom Metrics:** Visual builder for creating DQ rules from function templates
- **Function Catalog:** Browse available DQ functions with descriptions and usage
- **Master-Detail Views:** Expandable metric cards showing technical implementation details
- **Configuration Management:** View and edit monitoring settings for all tables

---

## 🎨 Portal Features

### 📊 Dashboard Page
Real-time visualization of data quality metrics across all monitored tables, embedded directly from Databricks SQL dashboards.

### ⚙️ Configuration Page
**Monitored Tables:**
- View all tables currently being monitored
- See profile type, schedule, and status
- Select table to view custom metrics

**Custom Metrics:**
- Master-detail view showing ratio metrics with expandable details
- View quality thresholds (Good/Acceptable/Bad)
- See function implementation and parameters
- Add new metrics from function catalog
- Delete existing metrics

### 📖 Function Catalog Page
Browse all available DQ functions organized by quality dimension:
- **COMPLETENESS** - Missing values, null ratios
- **VALIDITY** - Format checks, regex patterns, range validations
- **ACCURACY** - Business rule validations, referential integrity
- **CONSISTENCY** - Cross-field logic, relationship checks

Each function shows:
- Description and usage
- Input parameters with types
- Related functions (ratio + details pairs)
- Quality thresholds

### ➕ Register New Table
Step-by-step wizard for adding tables to monitoring:
1. Select catalog, schema, and table
2. Preview table data (10 rows)
3. Choose profile type (TimeSeries or Snapshot)
4. Configure timestamp column and granularities (for TimeSeries)
5. Set monitoring schedule
6. Enable/disable monitoring

### 🔍 Edit Table Configuration
Modify monitoring settings for existing tables:
- Update profile type and timestamp column
- Change granularities
- Adjust schedule
- Enable/disable monitoring
- View and manage custom metrics for the table

---
## 🛠️ Configuration

### Portal Configuration (`dq_app/app.yaml`)

Only one file to edit:

```yaml
command: ["python", "app.py"]

env:
  # Application-specific configuration
  - name: CATALOG
    value: "dbdemos_steventan"
  - name: ADMIN_SCHEMA
    value: "monitoring_admin"
  - name: DATA_SCHEMA
    value: "lakehouse_monitoring"
  - name: OUT_SCHEMA
    value: "lakehouse_monitoring_demo_results"
  - name: SQL_WAREHOUSE_ID
    value: "862f1d757f0424f7"
  - name: DATABRICKS_ORG_ID
    value: "1444828305810485"
  - name: DASHBOARD_ID
    value: "01f097746d9d1bbbbc0d7939c55bb781"
```

For detailed configuration instructions, see [`dq_app/CONFIGURATION.md`](dq_app/CONFIGURATION.md).

---

## 📐 Data Quality Dimensions

The framework organizes DQ rules by standard dimensions:

| Dimension | Description | Example Rules |
|-----------|-------------|---------------|
| **COMPLETENESS** | Data presence | Missing values, null ratios, required fields |
| **VALIDITY** | Format correctness | Email format, date ranges, regex patterns, enum values |
| **ACCURACY** | Data correctness | Range checks, referential integrity, business rules |
| **CONSISTENCY** | Cross-field logic | Field relationships, derived values, conditional rules |

Each dimension has associated SQL functions that can be bound to table columns through the portal.

---

## 🎯 Use Cases

### For Data Quality Stewards
- Register new tables for monitoring through the web UI
- Create custom quality checks without writing SQL
- Monitor quality trends across all tables
- Drill down into specific data quality issues

### For Data Engineers
- Define reusable DQ functions as SQL UDFs
- Extend the function catalog with domain-specific rules
- Automate monitoring job scheduling

### For Business Users
- View data quality dashboards
- Understand quality metrics by dimension
- Track quality improvements over time
- Identify tables requiring attention

---

## 🔧 Troubleshooting

### Dashboard Not Loading
- ✅ Ensure dashboard is **published**
- ✅ Enable **"Embed dashboards"** in workspace security settings
- ✅ Verify `DASHBOARD_ID` and `DATABRICKS_ORG_ID` are correct

### Cannot Connect to SQL Warehouse
- ✅ Check `SQL_WAREHOUSE_ID` in `app.yaml`
- ✅ Ensure app has `CAN_USE` permission on warehouse
- ✅ Verify warehouse is running

### Portal Not Loading
- ✅ Check app deployment logs in Databricks
- ✅ Verify all environment variables are set correctly
- ✅ Ensure metadata tables exist in the specified catalog/schema

### Cannot See Tables in Portal
**Problem:** Dropdowns are empty when trying to register tables or no tables appear in listings.

**Required Permissions:**
1. **BROWSE Permission** on Catalog/Schema:
   ```sql
   -- Grant browse permission on catalog
   GRANT USE CATALOG ON CATALOG <catalog_name> TO `<app_service_principal>`;
   
   -- Grant browse permission on schemas
   GRANT USE SCHEMA ON SCHEMA <catalog_name>.<schema_name> TO `<app_service_principal>`;
   ```

2. **SELECT Permission** on Tables:
   ```sql
   -- Grant select permission to read table data
   GRANT SELECT ON TABLE <catalog_name>.<schema_name>.<table_name> TO `<app_service_principal>`;
   ```

**Steps to Grant Permissions:**
1. Go to **Catalog** in Databricks UI
2. Navigate to the catalog/schema/table
3. Click **Permissions** tab
4. Add the app's service principal with appropriate permissions
5. Ensure `USE CATALOG`, `USE SCHEMA`, and `SELECT` are granted

### Cannot Create or Modify Metrics
**Problem:** "Permission denied" errors when adding/deleting custom metrics or registering tables.

**Required Permissions on Metadata Tables:**
```sql
-- Grant full permissions on metadata tables
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE <catalog>.monitoring_admin.monitors_control 
  TO `<app_service_principal>`;

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE <catalog>.monitoring_admin.metric_templates 
  TO `<app_service_principal>`;

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE <catalog>.monitoring_admin.metric_bindings 
  TO `<app_service_principal>`;
```

**Note:** The app's service principal name can be found in:
- **Apps** → Click your app → **Configuration** → Service Principal

### Metrics Not Appearing
- ✅ Check `enabled = TRUE` in `metric_bindings`
- ✅ Verify function exists in Unity Catalog
- ✅ Check monitoring job logs for errors
- ✅ Refresh the portal page
- ✅ Verify app has `SELECT` permission on `metric_bindings` table

---

## 📁 Repository Structure

```
lakehouse_monitoring/
├── notebooks/                                  # Databricks Notebooks
│   ├── 01_generate_sample_data.ipynb
│   ├── 02_metadata_table.ipynb
│   ├── 04_lakehouse_monitoring_functions.ipynb
│   ├── 05_additional_metadata_tables.ipynb
│   ├── 06_lakehouse_monitoring_API_v0.2.ipynb
│   ├── 07_results_view_creation.ipynb
│   └── 08_dashboard_template_rewriter.ipynb
│
├── dq_app/                                     # Self-Service Portal (NEW in v0.4)
│   ├── app.yaml                                # Configuration
│   ├── app.py                                  # Main Dash application
│   ├── db_utils.py                             # Database utilities
│   ├── requirements.txt                        # Python dependencies
│   ├── CONFIGURATION.md                        # Setup guide
│   └── QUICKSTART.md                           # Quick start guide
│
├── dashboards/                                 # Dashboard templates
│   └── Data Quality Dashboards Template.lvdash.json
│
└── README.md                                   # This file
```

---

## ✅ Summary

You now have a **complete metadata-driven data quality framework** with:
- ✅ Automated monitors (via APIs)  
- ✅ Reusable rule definitions (via SQL functions)  
- ✅ Unified analytics and visualization layer (via dynamic views)
- ✅ **Self-service web portal (via Databricks App)** — NEW in v0.4

This architecture ensures your data quality monitoring scales effortlessly as your lakehouse grows, while providing an intuitive interface for non-technical users.

---

## 🚀 What's New in v0.4

### Self-Service Portal
- 🎨 **Web-Based UI** - No more notebook editing for routine tasks
- 🔐 **OAuth Security** - Token-free authentication
- 📊 **Embedded Dashboards** - Real-time DQ visualization
- ➕ **Visual Table Registration** - Point-and-click onboarding
- 🎯 **Metric Builder** - Create DQ checks from templates
- 📖 **Function Catalog** - Browse available DQ rules
- 🔍 **Master-Detail Views** - Drill into metric configurations
- ⚙️ **Configuration Management** - Edit monitoring settings
---

## 🔜 Coming in v0.5

- **Anomaly Detection** - ML-based quality trend analysis
---

## 🤝 Contributing

To extend this framework:

1. **Add DQ Functions** - Create new SQL UDFs in `04_lakehouse_monitoring_functions.ipynb`
2. **Create Templates** - Add rows to `metric_templates` table
3. **Enhance Portal** - Modify `dq_app/app.py` for new features
4. **Update Docs** - Keep documentation in sync with changes

---
> ⭐ **Star this repo** and follow for **v0.5 — Anomaly Detection & Advanced Alerting**

