# 🧠 Lakehouse Monitoring on Databricks

**Version:** v0.1 — *Foundations of Lakehouse Data Quality Monitoring*

This repository introduces a practical, incremental approach to implementing **Lakehouse Monitoring** on Databricks using only native capabilities — no external orchestration or custom metrics required (yet).

The goal of **v0.1** is to set up the baseline building blocks for automated data quality profiling using **Databricks Lakehouse Monitoring API** and **Unity Catalog–managed metadata**.

---

## 📚 What’s Included

| Notebook | Description |
|-----------|--------------|
| `01_Generate_Sample_Data.ipynb` | Creates sample Delta tables (e.g., `policies`, `claims`, `premium_billing`) with realistic timestamp columns for monitoring. |
| `02_Metadata_Tables.ipynb` | Defines and populates the `monitors_control` metadata table — the single source of truth for which tables are monitored and how. |
| `03_Lakehouse_Monitoring_API.ipynb` | Reads from `monitors_control` and automatically creates/updates Databricks Lakehouse Monitors using the Workspace SDK. |

---

## ⚙️ Architecture Overview

At v0.1, the solution demonstrates a **metadata-driven monitoring pattern**:

monitors_control → Databricks Lakehouse Monitoring API → Automated Profile Metrics

Each record in `monitors_control` defines:
- **Catalog / Schema / Table** under monitoring  
- **Timestamp column** and **granularity** (e.g. `1 day`)  
- **Schedule & Timezone** for recurring jobs  
- **Output schema** for storing generated profile metrics  

This design allows you to add or remove monitored tables **just by editing metadata**, without touching code.

---

## 🚀 How to Run

1. **Clone this repo** or import into your Databricks workspace.  
2. **Open** the notebooks in sequence:
   - Run `01_Generate_Sample_Data`
   - Run `02_Metadata_Tables`
   - Run `03_Lakehouse_Monitoring_API`
3. Verify new monitors in **Data → Monitoring** UI on Databricks.

> 🟢 *Each monitor will automatically run profiling jobs on your sample tables.*

---

## 🧩 Design Philosophy

This project adopts a **bottom-up** approach:
- Start with *governed metadata tables*
- Automate API calls from metadata
- Later introduce *custom metrics* and *dashboard visualizations*

Upcoming versions will expand on:
- v0.2 → Add custom metric templates (`metric_templates`, `metric_bindings`)  
- v0.3 → Enrich dashboards with thresholds and DQ dimensions  
- v0.4 → Introduce a Databricks App for metadata input and control  

---

## 🧾 Example Metadata Record

| Field | Example | Description |
|--------|----------|-------------|
| `table_catalog` | `dbdemos_steventan` | Catalog for monitored table |
| `table_schema` | `lakehouse_monitoring` | Schema where data lives |
| `table_name` | `claims` | Table to be monitored |
| `timestamp_col` | `reported_at` | Column used for time series monitoring |
| `granularities` | `['1 day']` | Frequency of profiling |
| `output_schema_name` | `dbdemos_steventan.lakehouse_monitoring_results` | Where profile metrics are stored |
| `schedule_cron` | `0 0 * * * ?` | Daily schedule |
| `schedule_tz` | `Asia/Singapore` | Time zone |
| `enabled` | `true` | Activation flag |

---

## 🧭 Roadmap

| Version | Focus | Key Features |
|----------|--------|---------------|
| **v0.1** | Foundation | Auto-create monitors from `monitors_control` |
| **v0.2** | Custom Metrics | Add `metric_templates` + `metric_bindings` |
| **v0.3** | Visualization | Build Lakehouse DQ dashboards |
| **v0.4** | Databricks App | UI for managing metadata interactively |

---

## 🧑‍💻 Author

**Steven Tan, Databricks Solutions Architect (APJ)**  
Building end-to-end Lakehouse Monitoring frameworks for data reliability and governance.

🔗 Medium Blog (coming soon): *Lakehouse Monitoring Series — Part 1: The Foundations*  
📦 GitHub: [CheeYuTan/lakehouse_monitoring](https://github.com/CheeYuTan/lakehouse_monitoring)

---

> 💡 *If you find this useful, please ⭐ the repo and follow for updates on the next release!*
