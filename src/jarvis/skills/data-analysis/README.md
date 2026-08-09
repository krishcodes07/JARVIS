# Data Analysis Skill

> Inspect, clean, summarize, and extract actionable insights from structured data, log files, JSON/CSV datasets, and system metrics.

## Overview
The `data-analysis` skill provides a structured workflow for parsing dataset files, computing statistical metrics, identifying anomalies or patterns, and summarizing data into executive dashboards or markdown tables.

---

## When to Use
Use this skill when:
- Analyzing application performance logs, metric dumps, or error logs.
- Processing CSV, JSON, YAML, or SQL datasets to answer business or technical questions.
- Extracting trends, distributions, or key performance indicators (KPIs).

---

## Required & Recommended Tools
- `read_file` (to read data files or logs)
- `run_command` (to execute Python data analysis scripts using `pandas`, `sqlite3`, or stdlib tools)

---

## Step-by-Step Execution Protocol

### Step 1: Data Source Inspection & Validation
1. Inspect file format, row counts, column names, schema types, and sample entries.
2. Identify missing values, malformed records, or dirty data.

### Step 2: Data Cleaning & Normalization
1. Handle null values, duplicate records, and invalid data types.
2. Standardize timestamp formats, text casing, or numeric scaling where necessary.

### Step 3: Exploratory Data Analysis (EDA)
1. Calculate key summary metrics (Mean, Median, Min, Max, Percentiles, Standard Deviation).
2. Segment data by key dimensions or time windows.
3. Detect anomalies, outliers, clusters, or recurring trend patterns.

### Step 4: Insight Formulation & Visualization Summary
1. Draw meaningful conclusions based on empirical data distribution.
2. Construct markdown summary tables and clear textual charts.

### Step 5: Analytical Summary Presentation
Construct a clear markdown analysis report:

```markdown
# Data Analysis Summary: [Dataset Name]

## Executive Summary
- Primary finding 1
- Key trend 2

## Dataset Overview
- **Total Records**: 10,000
- **Time Range**: 2026-01-01 to 2026-08-01
- **Metrics Covered**: Latency, Throughput, Error Rate

## Key Findings & Metrics
| Metric | Average | P95 | Max | Status |
|--------|---------|-----|-----|--------|
| Latency| 45ms    | 120ms| 450ms| Normal |

## Identified Anomalies & Recommendations
- Spike detected on 2026-07-15 due to database backup job.
- Recommendation to reschedule cron execution window.
```
