# Budgetron Spending Analysis Tool

This repository contains Python scripts to analyze and visualize your financial transactions, helping you understand spending habits and track your budget effectively. The scripts are designed to work specifically with PayPal Mastercard statement exports in CSV format, but can be adapted for other transaction data with similar formatting.

---

## Requirements

- **Python**: Version 3.6 or later.
- **Libraries**:
  - `pandas`
  - `matplotlib`

Install the required libraries using pip:

```bash
pip install pandas matplotlib
```

---

## Scripts

### 1. `spending_categories.py`

This script processes a transaction CSV file, categorizes transactions based on keyword mappings, and visualizes total spending by category. It generates a bar chart summarizing categorized spending and lists transactions that could not be categorized.

#### Usage

```bash
python spending_categories.py <csv_file> <target_budget> <output_path>
```

#### Parameters

- `<csv_file>`: Path to the CSV file containing your transactions.
- `<target_budget>`: Your target spending budget for the period.
- `<output_path>`: Path to save the generated bar chart.

#### Example

```bash
python spending_categories.py transactions.csv 1000 categorized_spending.png
```

---

### 2. `graph_spending.py`

This script visualizes your spending over a 30-day period compared to a target budget. It reads a CSV file of transactions, calculates daily and cumulative spending, and generates a line plot for comparison.

#### Usage

```bash
python graph_spending.py <source_csv> <classification_csv> <target_budget> <output_path>
```

#### Parameters

- `<source_csv>`: Path to the CSV file containing raw transaction data.
- `<classification_csv>`: Path to a CSV file containing transaction classifications.
- `<target_budget>`: Your target budget over 30 days.
- `<output_path>`: Path to save the generated line plot.

#### Example

```bash
python graph_spending.py transactions.csv categories.csv 1500 spending_vs_budget.png
```

---

## Classification.csv Format

The `classification.csv` file is used to define the mappings between transaction descriptions and their corresponding spending categories. Each row in the file represents a specific keyword and its associated category.

### Format

| Grocery          | Take Out         | Coffee           | Eating Out      | Video Games      | Shopping          |
|------------------|------------------|------------------|-----------------|------------------|-------------------|
| stop and shop    | chipotle         | blue bottle coffee | chili's        | xbox games       | target            |
| market basket    | taco bell        | peet's coffee     | olive garden   | playstation games | ebay              |
| whole foods      | panda express    | dunkin' donuts    | red robin      | steam games      | vans              |
| hornstra farm    | pizza hut        | caribou coffee    | denny's        |                  | rei               |
| Stop & Shop      | boston market    | starbucks         | applebee's     |                  | etsy              |
|                  |                  |                   |                 |                  | urban outfitters  |
|                  |                  |                   |                 |                  | keeping pace with |
|                  |                  |                   |                 |                  | seoane landscaping|
|                  |                  |                   |                 |                  | gourmetgiftbaskets|

- **Categories**: The spending categories, such as Grocery, Take Out, etc., listed as column headers.
- **Keywords**: Business names or descriptors matching transactions, listed under the relevant categories.

Ensure that the file is saved in CSV format and that it contains a header row.

---

## License

This project is licensed under the MIT License.

