# 🧠 Lakehouse Monitoring on Databricks

**Version:** v0.3 — *Unified Data Quality Scorecard Views*

This release builds upon v0.2 by adding **dynamic result aggregation and visualization-ready views** — consolidating Lakehouse Monitoring outputs into a unified data quality layer.  

Instead of manually joining or querying each monitor’s results, v0.3 automatically generates consolidated views for:
- All metric results across tables (`dq_all_metrics`)
- Detailed offending-row diagnostics (`dq_all_metric_details`)
- Default profile statistics (`dq_all_metrics_default_profile`)

These serve as the foundation for downstream **Data Quality Scorecards** and **dashboards** — fully driven by metadata.

---

## 📚 What’s Included

| Notebook | Description |
|-----------|-------------|
| `01_generate_sample_data.ipynb` | Generates sample data tables for testing (`policies`, `claims`, `premium_billing`). |
| `02_metadata_table.ipynb` | Sets up the foundational `monitors_control` metadata table. |
| `04_lakehouse_monitoring_functions.ipynb` | Defines reusable SQL functions grouped by DQ dimensions (Validity, Completeness, Consistency, Accuracy). |
| `05_additional_metadata_tables.ipynb` | Creates the `metric_templates` and `metric_bindings` metadata tables. |
| `06_lakehouse_monitoring_API_v0.2.ipynb` | Registers Lakehouse Monitors using all metadata tables. |
| `07_results_view_creation.ipynb` | Builds three dynamic, consolidated views (`dq_all_metrics`, `dq_all_metric_details`, `dq_all_metrics_default_profile`) for downstream visualization. |
| `08_dashboard_template_rewriter.ipynb` | Utility notebook to adapt dashboard templates dynamically (replacing catalog/schema/view references). |

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

The entire pipeline now looks like this:
```
Metadata Tables + API Automation → Monitors → Profile & Custom Metrics → Unified Views → DQ Dashboard
```

This allows a single query or dashboard to visualize **all monitored tables**, automatically updated as new monitors are created.

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

1. Execute all previous setup notebooks (v0.1 and v0.2).  
2. Run the following notebooks sequentially:
   ```
   07_results_view_creation
   08_dashboard_template_rewriter
   ```
3. Inspect the generated views:
   ```sql
   SELECT * FROM dbdemos_steventan.lakehouse_monitoring_demo_results.dq_all_metrics;
   SELECT * FROM dbdemos_steventan.lakehouse_monitoring_demo_results.dq_all_metric_details;
   SELECT * FROM dbdemos_steventan.lakehouse_monitoring_demo_results.dq_all_metrics_default_profile;
   ```

4. (Optional) Use `Data Quality Dashboards Template.lvdash.json` under `/dashboards/` to render a unified visualization layer.

---

## 🧠 Design Highlights

- **Dynamic Metadata Joins:** Views are automatically assembled from metadata and monitor outputs — no static references.  
- **Cross-Table Aggregation:** Combines multiple monitor outputs into a single consistent schema.  
- **Extensible Structure:** New metrics and monitors automatically appear in dashboards.  
- **Zero Manual Overhead:** No code edits needed when new tables are onboarded.

---

## ✅ Summary

You now have a **metadata-driven data quality framework** with:
- Automated monitors (via APIs)  
- Reusable rule definitions (via SQL functions)  
- Unified analytics and visualization layer (via dynamic views)

This architecture ensures your data quality monitoring scales effortlessly as your lakehouse grows.

---

> ⭐ **Star this repo** and follow for **v0.4 — Automated DQ Dashboards and Anomaly Detection**
