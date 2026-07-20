# Analysis Report

> Executive summary: analysis of Analyse regional sales performance completed across 7 pipeline steps. Dataset has 205 rows, 5 duplicate rows, nulls in ['revenue']. Cleaning removed 5 rows (duplicates + unrecoverable nulls). Outlier check on 'revenue': 0 value(s) outside [-2,183, 7,374] (IQR method). Top region by total revenue: North (158,233 across 50 records). Full details in the attached report and chart.

## Key findings

- Dataset has 205 rows, 5 duplicate rows, nulls in ['revenue'].
- Cleaning removed 5 rows (duplicates + unrecoverable nulls).
- Outlier check on 'revenue': 0 value(s) outside [-2,183, 7,374] (IQR method).
- Top region by total revenue: North (158,233 across 50 records).

## Aggregation

| region   |      sum |    mean |   count |
|:---------|---------:|--------:|--------:|
| North    | 158233   | 3164.66 |      50 |
| West     | 150325   | 2947.55 |      51 |
| East     | 138325   | 2561.57 |      54 |
| South    |  84259.9 | 1872.44 |      45 |

## Chart

![chart](chart.png)