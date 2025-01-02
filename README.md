# Budgetron Spending Analysis Tool

This repository contains Python scripts to analyze and visualize your financial transactions, helping you understand spending habits and track your budget effectively. The scripts are designed to work specifically with PayPal Mastercard statement exports in CSV format, but can be adapted for other transaction data with similar formatting.

---

## Requirements

- **Python**: Version 3.6 or later.
- **Libraries**:
  - `pandas`
  - `matplotlib`
  - `requests`

Install the required libraries using pip:

```bash
pip install pandas matplotlib requests
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

### 3. `driver_analysis.py`

This script automates the analysis process by identifying the latest transaction file for the previous month, running analysis scripts, and sending notifications via Discord.

#### Usage

```bash
python driver_analysis.py --folder <csv_folder> --classification_csv <classification_csv> --budget <budget> --bot_token <bot_token> --channel_id <channel_id>
```

#### Parameters

- `--folder`: Folder containing CSV files for transactions.
- `--classification_csv`: Path to the CSV file for spending classifications.
- `--budget`: Target spending budget.
- `--bot_token`: Discord bot token for notifications.
- `--channel_id`: Discord channel ID for posting updates.

#### Example

```bash
python driver_analysis.py --folder ./transactions --classification_csv categories.csv --budget 2000 --bot_token BOT_TOKEN --channel_id 123456789012345678
```

---

### 4. `post_to_discord.py`

This script posts messages and images to a Discord channel, optionally processing messages with OpenAI’s ChatGPT for better phrasing.

#### Usage

```bash
python post_to_discord.py <bot_token> <channel_id> <message> [<image_path>]
```

#### Parameters

- `<bot_token>`: Discord bot token for authentication.
- `<channel_id>`: ID of the Discord channel where the message will be posted.
- `<message>`: Text message to be posted.
- `<image_path>` (optional): Path to an image file to include with the message.

#### Example

```bash
python post_to_discord.py BOT_TOKEN 123456789012345678 "Budget analysis complete!" spending_graph.png
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

- **Categories**: The spending categories, such as Grocery, Take Out, etc., listed as column headers.
- **Keywords**: Business names or descriptors matching transactions, listed under the relevant categories.

Ensure that the file is saved in CSV format and that it contains a header row.

---

## License

This project is licensed under the MIT License.

