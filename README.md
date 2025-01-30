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

### 5. `check_csv_file.py`

This script checks for the presence of a CSV file for the current month and year in a specified folder. If a file is found, it sends a notification to a Discord channel. This is useful for ensuring that transaction data is uploaded in a timely manner.

#### Usage

```bash
python check_csv_file.py --folder <csv_folder> --bot_token <bot_token> --channel_id <channel_id>
```

#### Parameters

- `--folder`: Folder containing the CSV files.
- `--bot_token`: Discord bot token for sending notifications.
- `--channel_id`: Discord channel ID where notifications will be posted.

#### Example

```bash
python check_csv_file.py --folder ./transactions --bot_token BOT_TOKEN --channel_id 123456789012345678
```

#### Functionality

- Searches for a CSV file with the format `<Month> <Year> -*.csv` (e.g., "December 2024 -*.csv").
- Sends a notification to Discord indicating whether the file was found or not.

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

## Example Discord Output

![Example Discord Output](https://budgetron-storage-public.s3.us-east-1.amazonaws.com/PostExample.png)

### 6. 'fetch_google_drive.py'

This script allows you to download files from Google Drive using the Google Drive API.

#### Prerequisites

1. **Google Cloud Credentials**:
   - Obtain a `credentials.json` file from the Google Cloud Console. This file is required for OAuth authentication.
   - Place the `credentials.json` file in the same directory as the script.

2. **Install Required Libraries**:
   - Install the required Python libraries using pip:
     ```bash
     pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client
     ```

3. **Set Up Environment**:
   - Ensure you have Python 3.7 or later installed.
   - Verify you have access to the file you want to download from Google Drive.

#### How to Use

#### Command-Line Usage

Run the script using the following syntax:

```bash
python fetch_google_drive.py <file_id> <destination_path> [--mime_type <mime_type>]
```

#### Required Arguments:
- `<file_id>`: The unique ID of the file on Google Drive. You can find this in the file's URL (e.g., `https://drive.google.com/file/d/<file_id>/view`).
- `<destination_path>`: The path where the downloaded file will be saved. Include the file name and extension (e.g., `./classification.csv`).

#### Optional Argument:
- `--mime_type`: Specify the MIME type for export. For example, use `text/csv` to download a Google Sheets file as a CSV.

#### Example Commands

1. **Download a File in Its Original Format**:
   ```bash
   python fetch_google_drive.py 1A2B3C4D5E6F7G8H9I0J ./output_file.txt
   ```

2. **Download a Google Sheet as CSV**:
   ```bash
   python fetch_google_drive.py 1A2B3C4D5E6F7G8H9I0J ./output_file.csv --mime_type text/csv
   ```

#### Notes

- On the first run, the script will open a browser window for OAuth authentication. This generates a `token.json` file for future use.
- Ensure the script has write permissions for the specified `destination_path`.
- The `token.json` file allows the script to authenticate without requiring repeated logins. If deleted, you will need to reauthenticate.

#### Troubleshooting

#### Common Issues

1. **`token.json` Errors**:
   - If you encounter errors related to `token.json` (e.g., corruption or missing fields), delete the file and rerun the script to regenerate it.

2. **Permission Denied**:
   - Verify write permissions for the destination directory. Do you have the file open?

3. **`redirect_uri_mismatch` Error**:
   - Ensure the redirect URI is configured correctly in the Google Cloud Console.

## License

This project is licensed under the MIT License.

