# Requirements

- **Python**: Version 3.6 or later.
- **Libraries**:
  - `pandas`
  - `matplotlib`

Install the required libraries using pip:

```bash
pip install pandas matplotlib
```

# Scripts

## spending_categories.py

This Python script processes a transaction CSV file, categorizes transactions using keyword mappings, and visualizes total spending by category over a specific period. It outputs a bar chart summarizing categorized spending and highlights transactions that could not be categorized.

---

### Example

```bash
python spending_categories.py <csv_file> <target_budget> <output_path>
```

## graph_spending.py

This script visualizes your spending against a target budget over a 30-day period. It reads a CSV file of transactions, calculates daily and cumulative spending, and compares it to your specified budget using a line plot.

---

### Example

```bash
python graph_spending_spending.py <source_csv> <classification_csv> <output_image>
```