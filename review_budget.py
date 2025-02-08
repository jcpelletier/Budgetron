import os
import sys
import pandas as pd
import datetime
import requests


# Function to get last two months' filenames
def get_last_two_months_files(folder_path):
    today = datetime.date.today()
    first_day_of_this_month = today.replace(day=1)

    last_month = first_day_of_this_month - datetime.timedelta(days=1)
    month_before_last = last_month.replace(day=1) - datetime.timedelta(days=1)

    last_month_filename = f"{last_month.strftime('%B %Y')} - transactions.csv"
    month_before_last_filename = f"{month_before_last.strftime('%B %Y')} - transactions.csv"

    last_month_path = os.path.join(folder_path, last_month_filename)
    month_before_last_path = os.path.join(folder_path, month_before_last_filename)

    return last_month_path, month_before_last_path


# Function to concatenate last two months' transactions
def concatenate_transactions(folder_path):
    file1, file2 = get_last_two_months_files(folder_path)

    # Check if both files exist
    if not os.path.exists(file1):
        print(f"Error: Missing file {file1}")
        sys.exit(1)
    if not os.path.exists(file2):
        print(f"Error: Missing file {file2}")
        sys.exit(1)

    # Load CSV files
    df1 = pd.read_csv(file1)
    df2 = pd.read_csv(file2)

    # Combine data
    combined_df = pd.concat([df1, df2], ignore_index=True)

    # Save to new file
    output_file = os.path.join(folder_path, "combined_transactions.csv")
    combined_df.to_csv(output_file, index=False)

    return output_file, combined_df


# Function to process the transactions with OpenAI API
def analyze_transactions(api_key, budget, transactions_csv):
    # Read CSV content
    transactions_data = pd.read_csv(transactions_csv)

    # Convert to JSON string (or structured text)
    transactions_text = transactions_data.to_string(index=False)

    # Prompt
    prompt_text = f"""
    Review my transactions for last month and tell me how I did vs my budget of ${budget}. 
    Summarize where most of my spending went and how it compares to the previous month.

    Transactions Data:
    {transactions_text}
    """

    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    data = {
        "model": "gpt-4",
        "messages": [
            {"role": "system", "content": "You are a financial assistant reviewing personal spending data."},
            {"role": "user", "content": prompt_text},
        ],
        "max_tokens": 300,
    }

    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    except requests.exceptions.HTTPError as e:
        print(f"HTTP error interacting with OpenAI API: {e}")
    except requests.exceptions.RequestException as e:
        print(f"Request error: {e}")

    return None


# Main script execution
if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: python review_budget.py <folder_path> <budget> <openai_api_key>")
        sys.exit(1)

    folder_path = sys.argv[1]
    budget = int(sys.argv[2])
    openai_api_key = sys.argv[3]

    # Get combined transactions file
    transactions_file, _ = concatenate_transactions(folder_path)

    # Analyze transactions with OpenAI
    analysis_result = analyze_transactions(openai_api_key, budget, transactions_file)

    if analysis_result:
        print("\nFinancial Analysis:")
        print(analysis_result)
