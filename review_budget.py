import os
import sys
import argparse # Added argparse
import pandas as pd
import datetime
import requests
import calendar # Added calendar


# Function to get last n months' filenames
def get_last_n_months_files(folder_path, num_months, billing_cutoff_day):
    today = datetime.date.today()
    file_paths = []

    actual_num_months_to_fetch = num_months
    if billing_cutoff_day is not None:
        actual_num_months_to_fetch = num_months + 1
        print(f"Billing cutoff day is set ({billing_cutoff_day}), fetching data for {actual_num_months_to_fetch} calendar months to cover {num_months} billing cycle(s).")
    else:
        print(f"Billing cutoff day not set, fetching data for {num_months} calendar months.")


    current_month = today.replace(day=1)

    for _ in range(actual_num_months_to_fetch):
        # Move to the first day of the previous month
        current_month = current_month - datetime.timedelta(days=1)
        current_month = current_month.replace(day=1)
        
        filename = f"{current_month.strftime('%B %Y')} - transactions.csv"
        file_path = os.path.join(folder_path, filename)
        file_paths.append(file_path)

    return file_paths


# Function to concatenate last n months' transactions
def concatenate_transactions(folder_path, num_months, billing_cutoff_day): # Added billing_cutoff_day
    files = get_last_n_months_files(folder_path, num_months, billing_cutoff_day) # Pass billing_cutoff_day
    
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


# Function to segment transactions by billing cycle
def segment_transactions_by_billing_cycle(df, num_billing_cycles, billing_cutoff_day, reference_date=None):
    """
    Segments transactions from a DataFrame based on a specified number of billing cycles.

    Args:
        df (pd.DataFrame): Input DataFrame with a 'Date' column for transaction dates.
        num_billing_cycles (int): Number of billing cycles to extract.
        billing_cutoff_day (int): Day of the month for billing cutoff (1-31).
        reference_date (datetime.date, optional): "Today" for calculations. Defaults to datetime.date.today().

    Returns:
        pd.DataFrame: Filtered DataFrame containing transactions for the requested billing cycles.
    """
    if reference_date is None:
        reference_date = datetime.date.today()

    # Convert 'Date' column to datetime objects
    original_len = len(df)
    df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
    
    # Handle rows with unparseable dates
    if df['Date'].isnull().any():
        num_invalid_dates = df['Date'].isnull().sum()
        print(f"Warning: Dropped {num_invalid_dates} rows due to unparseable dates.")
        df.dropna(subset=['Date'], inplace=True)
    
    if df.empty:
        print("Warning: DataFrame is empty after handling invalid dates. Returning empty DataFrame.")
        return df

    all_cycle_start_dates = []
    all_cycle_end_dates = []

    for i in range(num_billing_cycles):
        # Calculate cycle_end_date for the i-th previous cycle
        current_ref_year = reference_date.year
        current_ref_month = reference_date.month
        
        # Adjust month and year to go back i months
        # (reference_date.month - 1) to make it 0-indexed for easier modulo arithmetic
        # then subtract i, then add 1 back.
        effective_month_num = (current_ref_month - 1) - i 
        year_offset = effective_month_num // 12
        
        target_year = current_ref_year + year_offset
        target_month = (effective_month_num % 12) + 1

        # Determine the actual last day for the billing cutoff in the target month
        _, max_days_in_target_month = calendar.monthrange(target_year, target_month)
        actual_cutoff_day_for_end = min(billing_cutoff_day, max_days_in_target_month)
        cycle_end_date = datetime.date(target_year, target_month, actual_cutoff_day_for_end)
        all_cycle_end_dates.append(cycle_end_date)

        # Calculate cycle_start_date (day after previous cycle's end date)
        # Go to the first day of the cycle_end_date's month, then go back one day to get previous month's end
        prev_month_end_ref_day = cycle_end_date.replace(day=1) - datetime.timedelta(days=1)
        
        start_cycle_year = prev_month_end_ref_day.year
        start_cycle_month = prev_month_end_ref_day.month

        # Determine the actual last day for the billing cutoff in the *previous* month
        _, max_days_in_start_prev_month = calendar.monthrange(start_cycle_year, start_cycle_month)
        actual_cutoff_day_for_start_prev = min(billing_cutoff_day, max_days_in_start_prev_month)
        
        cycle_start_date = datetime.date(start_cycle_year, start_cycle_month, actual_cutoff_day_for_start_prev) + datetime.timedelta(days=1)
        all_cycle_start_dates.append(cycle_start_date)

    if not all_cycle_start_dates or not all_cycle_end_dates:
        print("Warning: Could not determine any billing cycle date ranges. Returning empty DataFrame.")
        return pd.DataFrame(columns=df.columns)

    overall_earliest_start_date = min(all_cycle_start_dates)
    overall_latest_end_date = max(all_cycle_end_dates)
    
    print(f"Filtering transactions from {overall_earliest_start_date.strftime('%Y-%m-%d')} to {overall_latest_end_date.strftime('%Y-%m-%d')}")

    # Filter the DataFrame
    # Ensure comparison is between datetime objects (pd.Timestamp from to_datetime vs. datetime.datetime)
    # Convert overall dates to pd.Timestamp for robust comparison, as df['Date'] are Timestamps
    filtered_df = df[
        (df['Date'] >= pd.to_datetime(overall_earliest_start_date)) & 
        (df['Date'] <= pd.to_datetime(overall_latest_end_date))
    ]

    return filtered_df


# Function to process the transactions with OpenAI API
def analyze_transactions(api_key, budget, transactions_df, num_months, billing_cutoff_day): # Updated signature
    # Convert DataFrame to JSON string (or structured text)
    # The input is now a DataFrame transactions_df
    if transactions_df.empty:
        print("Warning: analyze_transactions received an empty DataFrame. No analysis will be performed.")
        return "No transaction data to analyze."
        
    transactions_text = transactions_df.to_string(index=False)

    # Determine period_string and context for the prompt based on billing_cutoff_day
    period_descriptor = "month" if num_months == 1 else "months"
    period_context_details = f"over these {num_months} calendar {period_descriptor}"

    if billing_cutoff_day is not None:
        period_descriptor = "billing period" if num_months == 1 else "billing periods"
        period_string = f"last {num_months} {period_descriptor}"
        period_context_details = (
            f"where each billing period ends on approximately day {billing_cutoff_day} of the month. "
            f"Analyze my spending patterns across these {num_months} billing periods."
        )
    else:
        period_string = f"last {num_months} calendar {period_descriptor}"
        period_context_details = f"Analyze my spending patterns over these {num_months} calendar {period_descriptor}."


    # Prompt
    prompt_text = f"""
    Review my transactions for the {period_string}. {period_context_details}
    Tell me how I did against my budget of ${budget}.
    Summarize where most of my spending went.
    Identify if my overall spending is increasing or decreasing across this period.
    Note any other significant trends, patterns, or anomalies you observe in the spending data.

    Transactions Data:
    {transactions_text}
    """

    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    data = {
        "model": "o4-mini",
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
    parser = argparse.ArgumentParser(
        description="Concatenates transaction CSVs from the last N months and sends data to OpenAI for financial analysis."
    )
    parser.add_argument(
        "folder_path", 
        help="Path to the folder containing the monthly transaction CSV files (e.g., 'January 2024 - transactions.csv')."
    )
    parser.add_argument(
        "num_months", 
        type=int, 
        help="Number of recent months of transaction data to analyze (e.g., 3 for the last 3 months)."
    )
    parser.add_argument(
        "budget", 
        type=int, 
        help="Your total budget amount for the period analyzed."
    )
    parser.add_argument(
        "openai_api_key", 
        help="Your OpenAI API key."
    )
    parser.add_argument(
        "--billing_cutoff_day", 
        type=int, 
        choices=range(1, 32), 
        default=None,
        help="Day of the month transactions are cut off for billing (1-31). If provided, analysis will be based on billing cycles ending on this day."
    )
    
    args = parser.parse_args()

    # The print statement about billing_cutoff_day being provided or not will now be inside get_last_n_months_files
    # if it's set, or just before the loop in that function.
    # We can remove the one here to avoid redundancy, or keep it if explicit top-level confirmation is desired.
    # For now, let's keep it for clarity at the script's start.
    if args.billing_cutoff_day is not None:
        print(f"Script started with billing cutoff day: {args.billing_cutoff_day}")
    else:
        print("Script started without billing cutoff day. Using calendar months.")


    # Get combined transactions file
    output_csv_path, raw_combined_df = concatenate_transactions(args.folder_path, args.num_months, args.billing_cutoff_day)

    processed_df = raw_combined_df

    if args.billing_cutoff_day is not None and processed_df is not None and not processed_df.empty:
        print(f"Billing cutoff day ({args.billing_cutoff_day}) provided. Segmenting transactions by billing cycle.")
        # Pass datetime.date.today() explicitly as reference_date, though it's the default in the function
        processed_df = segment_transactions_by_billing_cycle(
            raw_combined_df, 
            args.num_months, 
            args.billing_cutoff_day,
            reference_date=datetime.date.today() 
        )
        if processed_df.empty:
            print("No transactions found within the specified billing cycles after segmentation.")
    elif processed_df is None or processed_df.empty : # This handles if raw_combined_df was initially empty
        print("No transaction data to process from concatenate_transactions.")


    # The condition to proceed with analysis should depend on processed_df
    if processed_df is not None and not processed_df.empty:
        analysis_result = analyze_transactions(
            args.openai_api_key, 
            args.budget, 
            processed_df, # Pass the processed DataFrame
            args.num_months, 
            args.billing_cutoff_day # Pass billing_cutoff_day
        )

        if analysis_result:
            print("\nFinancial Analysis:")
            print(analysis_result)
    else:
        # This message will now be triggered if raw_combined_df was empty OR 
        # if processed_df became empty after segmentation.
        print("Skipping analysis as no transaction data was available or found for the specified criteria.")
