import sys
import time
import csv
from datetime import datetime, timedelta
from plaid.api import plaid_api
from plaid.model.item_public_token_exchange_request import ItemPublicTokenExchangeRequest
from plaid.model.transactions_get_request import TransactionsGetRequest
from plaid.model.transactions_get_request_options import TransactionsGetRequestOptions
from plaid.configuration import Configuration
from plaid.api_client import ApiClient

def fetch_transactions(client_id, secret, link_token, max_retries=5, delay=10, output_file="transactions.csv"):
    # Setup Plaid API configuration
    configuration = Configuration(
        host="https://production.plaid.com",
        api_key={
            'clientId': client_id,
            'secret': secret
        }
    )
    api_client = ApiClient(configuration)
    client = plaid_api.PlaidApi(api_client)

    try:
        # Exchange the public token for an access token
        exchange_request = ItemPublicTokenExchangeRequest(public_token=link_token)
        exchange_response = client.item_public_token_exchange(exchange_request)
        access_token = exchange_response.access_token

        # Calculate the date range for the last 10 days
        end_date = datetime.now().date()
        start_date = (datetime.now() - timedelta(days=10)).date()

        # Retry mechanism for fetching transactions
        for attempt in range(max_retries):
            try:
                transactions_request = TransactionsGetRequest(
                    access_token=access_token,
                    start_date=start_date,
                    end_date=end_date,
                    options=TransactionsGetRequestOptions(
                        count=100,  # Maximum number of transactions per request
                        offset=0  # Offset for pagination
                    )
                )

                # Fetch transactions
                response = client.transactions_get(transactions_request)
                transactions = response.transactions

                # Write transactions to a CSV file
                with open(output_file, mode='w', newline='', encoding='utf-8') as csv_file:
                    writer = csv.writer(csv_file)
                    writer.writerow(["Date", "Description", "Amount"])  # CSV header

                    print("Date, Description, Amount")  # Print header to console
                    for transaction in transactions:
                        # Write to CSV
                        writer.writerow([transaction.date, transaction.name, transaction.amount])
                        # Print to console
                        print(f"{transaction.date}, {transaction.name}, {transaction.amount}")

                print(f"Transactions saved to {output_file}")
                return  # Exit function on success

            except Exception as e:
                if 'PRODUCT_NOT_READY' in str(e):
                    print(f"Attempt {attempt + 1}/{max_retries}: Product not ready. Retrying in {delay} seconds...")
                    time.sleep(delay)
                else:
                    raise  # Re-raise other exceptions

        print("Failed to fetch transactions after multiple retries.")

    except Exception as e:
        print(f"Error fetching transactions: {e}")

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python fetch_transactions.py <client_id> <secret> <link_token>")
        sys.exit(1)

    client_id = sys.argv[1]
    secret = sys.argv[2]
    link_token = sys.argv[3]

    fetch_transactions(client_id, secret, link_token)
