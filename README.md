# 🧠 Lakehouse Monitoring on Databricks

**Version:** v0.2 — *Custom Metrics & Metadata-Driven Quality Rules*

This release extends the v0.1 foundation by introducing **custom metric templates and bindings**, allowing teams to define reusable data quality rules and automatically attach them to tables — all through metadata.

The goal of **v0.2** is to make **Lakehouse Monitoring fully metadata-driven**:
- No more hardcoding metric logic  
- No manual monitor creation  
- Full lifecycle controlled from Unity Catalog tables  

---

## 📚 What’s Included

| Notebook | Description |
|-----------|--------------|
| `01_generate_sample_data.ipynb` | Generates sample Delta tables (`policies`, `claims`, `premium_billing`) for demonstration. |
| `02_metadata_table.ipynb` | Defines the foundational `monitors_control` table that drives monitor creation. |
| `04_lakehouse_monitoring_functions.ipynb` | Defines reusable SQL functions grouped by **data quality dimensions** (Validity, Completeness, Consistency, Accuracy). |
| `05_additional_metadata_tables.ipynb` | Adds new metadata tables — `metric_templates` and `metric_bindings` — to capture reusable metric logic and per-table associations. |
| `06_lakehouse_monitoring_API_v0.2.ipynb` | Automatically composes monitors from `metric_bindings` and registers both ratio and detailed JSON metrics. |

---

## ⚙️ Architecture Overview

### v0.1 — Foundations
```
monitors_control → Databricks Lakehouse Monitoring API → Profile Metrics
```

### v0.2 — Custom Metrics Layer
```
SQL Functions  →  Metric Templates  →  Metric Bindings  →  Monitors Control  →  Monitoring API
   ↑                 ↑                     ↑                      ↑
│ reusable rules  │ metric expressions  │ table attachments     │ orchestration
```

This modular design lets you:
- Centrally define **metric templates** once (e.g., “missing_value_ratio”).
- Reuse them across tables via **metric bindings**.
- Run all monitors automatically using metadata.

---

## 🧩 Key Metadata Tables

| Table | Purpose | Example Entry |
|--------|----------|---------------|
| `monitors_control` | Controls which tables are monitored, with scheduling and output configuration. | Table = `claims`, Granularity = `1 day`, Enabled = `true` |
| `metric_templates` | Defines reusable metric expressions (SQL with placeholders). | `avg(rule_missing_value_ratio_bit({VAL_COL}))` |
| `metric_bindings` | Binds templates to actual tables and columns. | `claims` → `negative_amount_ratio`, `AMOUNT_COL = claim_amount` |

---

## 🧮 Example Custom Metrics

| Dimension | Metric Name | Definition (SQL) | Purpose |
|------------|--------------|------------------|----------|
| **Completeness** | `missing_value_ratio` | `avg(rule_missing_value_ratio_bit(policy_no))` | Detects NULL or blank keys |
| **Validity** | `negative_amount_ratio` | `avg(rule_negative_amount_ratio_bit(claim_amount))` | Checks for negative amounts |
| **Consistency** | `inconsistent_closed_claims_ratio` | `avg(rule_inconsistent_closed_claims_ratio_bit(status, closed_at))` | Ensures closed claims have `closed_at` |
| **Accuracy** | `premium_out_of_range_ratio` | `avg(rule_premium_out_of_range_ratio_bit(amount_due))` | Validates business range thresholds |

Each metric also has a `_details_json` variant that captures offending rows as structured JSON for diagnostics.

---

## 🚀 How to Run

1. **Run notebooks sequentially:**
   - `01_generate_sample_data`
   - `02_metadata_table`
   - `04_lakehouse_monitoring_functions`
   - `05_additional_metadata_tables`
   - `06_lakehouse_monitoring_API_v0.2`
2. Verify all monitors in **Data → Monitoring** UI.
3. Optionally, inspect the control tables in Unity Catalog:
   ```sql
   SELECT * FROM dbdemos_steventan.monitoring_admin.metric_templates;
   SELECT * FROM dbdemos_steventan.monitoring_admin.metric_bindings;
   ```

---

## 🧠 Design Principles

- **Reusable Logic:** Metrics built from SQL functions, versioned under Unity Catalog.  
- **Metadata-Driven:** No hardcoding — everything controlled via metadata tables.  
- **Governed Automation:** One command regenerates all monitors.  
- **Separation of Concerns:** Metric logic (templates) decoupled from table bindings.  

---

> ⭐ **Star this repo** and follow for the upcoming v0.3 — Anomaly detection!
