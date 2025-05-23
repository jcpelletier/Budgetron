import os
import sys
import pandas as pd
import datetime
import requests


# Function to get last n months' filenames
def get_last_n_months_files(folder_path, num_months):
    today = datetime.date.today()
    file_paths = []

    current_month = today.replace(day=1)

    for _ in range(num_months):
        # Move to the first day of the previous month
        current_month = current_month - datetime.timedelta(days=1)
        current_month = current_month.replace(day=1)
        
        filename = f"{current_month.strftime('%B %Y')} - transactions.csv"
        file_path = os.path.join(folder_path, filename)
        file_paths.append(file_path)

    return file_paths


# Function to concatenate last n months' transactions
def concatenate_transactions(folder_path, num_months):
    files = get_last_n_months_files(folder_path, num_months)
    
    dfs = []
    found_files_count = 0
    for file_path in files:
        if os.path.exists(file_path):
            try:
                dfs.append(pd.read_csv(file_path))
                found_files_count += 1
            except Exception as e:
                print(f"Error reading file {file_path}: {e}")
        else:
            print(f"Info: Missing file {file_path}, skipping.")

    if not dfs:
        print("Error: No transaction files found for the specified period.")
        sys.exit(1)
    
    print(f"Found and successfully read {found_files_count} transaction file(s).")
    # Combine data
    combined_df = pd.concat(dfs, ignore_index=True)

    # Save to new file
    output_file = os.path.join(folder_path, "combined_transactions.csv")
    combined_df.to_csv(output_file, index=False)

    return output_file, combined_df


# Function to process the transactions with OpenAI API
def analyze_transactions(api_key, budget, transactions_csv, num_months):
    # Read CSV content
    transactions_data = pd.read_csv(transactions_csv)

    # Convert to JSON string (or structured text)
    transactions_text = transactions_data.to_string(index=False)

    # Determine month_string for the prompt
    month_string = f"last {num_months} months" if num_months > 1 else "last month"

    # Prompt
    prompt_text = f"""
    Review my transactions for the {month_string} and tell me how I did against my budget of ${budget}.
    Summarize where most of my spending went.
    Identify if my overall spending is increasing or decreasing across this period.
    Note any other significant trends, patterns, or anomalies you observe in the spending data over these {num_months} months.

    Transactions Data:
    {transactions_text}
    """

    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    data = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": "You are a financial assistant reviewing personal spending data."},
            {"role": "user", "content": prompt_text},
        ],
        "max_tokens": 500, # Increased max_tokens for potentially longer analysis
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
    if len(sys.argv) < 5: # Updated to reflect the new num_months argument
        print("Usage: python review_budget.py <folder_path> <num_months> <budget> <openai_api_key>")
        sys.exit(1)

    folder_path = sys.argv[1]
    num_months = int(sys.argv[2]) # Added num_months argument
    budget = int(sys.argv[3])
    openai_api_key = sys.argv[4]

    # Get combined transactions file
    transactions_file, combined_df = concatenate_transactions(folder_path, num_months) # Pass num_months

    if combined_df is not None and not combined_df.empty:
        # Analyze transactions with OpenAI
        analysis_result = analyze_transactions(openai_api_key, budget, transactions_file, num_months) # Pass num_months

        if analysis_result:
            print("\nFinancial Analysis:")
            print(analysis_result)
    else:
        print("Skipping analysis as no transaction data was found or processed.")
