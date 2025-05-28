import unittest
from unittest.mock import patch, MagicMock, call
import sys
import os
from datetime import datetime, date, timedelta # Ensure date is imported
import time # Will be mocked
import csv # For mocking csv.writer

# Attempt to import from fetch_transactions.py
try:
    from fetch_transactions import (
        fetch_transactions, # The main function to test
        main as fetch_transactions_main 
    )
    from plaid.exceptions import ApiException
    from plaid.model.plaid_error import PlaidError # For constructing error bodies
    # Required Plaid models for mocking responses
    from plaid.model.sandbox_public_token_create_response import SandboxPublicTokenCreateResponse
    from plaid.model.item_public_token_exchange_response import ItemPublicTokenExchangeResponse
    from plaid.model.transactions_get_response import TransactionsGetResponse
    from plaid.model.transaction import Transaction as PlaidTransaction # Alias to avoid clash with any other Transaction
    from plaid.model.account_base import AccountBase
    # For sandbox_public_token_create request
    from plaid.model.item_public_token_create_request_options import ItemPublicTokenCreateRequestOptions
    from plaid.model.products import Products
    from plaid.model.country_code import CountryCode

except ImportError:
    print("Note: Could not import from fetch_transactions.py or its Plaid dependencies. Tests will proceed with mocks.")
    class ApiException(Exception):
        def __init__(self, status=None, reason=None, body=None, headers=None, link_code=None, error_type=None, error_code=None, display_message=None, causes=None):
            self.status, self.reason, self.body, self.headers = status, reason, body, headers
            self.link_code, self.error_type, self.error_code, self.display_message, self.causes = link_code, error_type, error_code, display_message, causes
            super().__init__(display_message or reason)

    class PlaidError:
        def __init__(self, error_type, error_code, error_message, display_message=None, status_code=None):
            self.error_type, self.error_code, self.error_message = error_type, error_code, error_message
            self.display_message, self.status_code, self.causes = display_message, status_code, []
            self.request_id = "mock_request_id"

    class Products: TRANSACTIONS = "transactions"
    class CountryCode: US = "US"
    class SandboxPublicTokenCreateResponse: pass
    class ItemPublicTokenExchangeResponse: pass
    class TransactionsGetResponse: pass
    class PlaidTransaction: pass # Renamed
    class AccountBase: pass
    class ItemPublicTokenCreateRequestOptions: pass

    fetch_transactions = MagicMock()
    fetch_transactions_main = MagicMock()


# Mock pandas if not installed (fetch_transactions.py writes CSV directly)
# No pandas needed for these tests based on the refactored script.

# Helper function to create a mock Plaid API client instance
def get_mock_plaid_api_client_instance():
    mock_client = MagicMock()
    mock_client.sandbox_public_token_create = MagicMock()
    mock_client.item_public_token_exchange = MagicMock()
    mock_client.transactions_get = MagicMock()
    return mock_client

class TestFetchPlaidTransactions(unittest.TestCase):

    def setUp(self):
        self.client_id = "test_client_id"
        self.secret = "test_secret"
        self.output_file = "test_transactions.csv"
        self.default_max_retries = 3 # As per fetch_transactions.py default
        self.default_delay = 1     # As per fetch_transactions.py default

        # Keep Plaid client patches, as fetch_transactions creates the client internally
        self.mock_plaid_configuration_patch = patch('fetch_transactions.plaid.Configuration')
        self.mock_plaid_api_client_constructor_patch = patch('fetch_transactions.plaid.ApiClient')
        self.mock_plaid_api_factory_patch = patch('fetch_transactions.plaid_api.PlaidApi')

        self.mock_plaid_configuration = self.mock_plaid_configuration_patch.start()
        self.mock_plaid_api_client_constructor = self.mock_plaid_api_client_constructor_patch.start()
        self.mock_plaid_api_factory = self.mock_plaid_api_factory_patch.start()
        
        # This mock_api_client_instance will be returned by PlaidApi()
        self.mock_api_client_instance = get_mock_plaid_api_client_instance()
        self.mock_plaid_api_factory.return_value = self.mock_api_client_instance

        self.addCleanup(patch.stopall)

    # Obsolete test: test_create_plaid_client_initialization removed.

    @patch('builtins.open', new_callable=mock_open)
    @patch('fetch_transactions.csv.writer') # Mock csv.writer
    def test_fetch_transactions_success(self, mock_csv_writer, mock_open_file):
        """Test successful fetching and processing of transactions including token exchange."""
        
        # 1. Mock sandbox_public_token_create
        mock_public_token_response = SandboxPublicTokenCreateResponse(
            public_token="test_public_token", request_id="req_pt_create"
        )
        self.mock_api_client_instance.sandbox_public_token_create.return_value = mock_public_token_response

        # 2. Mock item_public_token_exchange
        mock_exchange_response = ItemPublicTokenExchangeResponse(
            access_token="test_access_token_from_exchange", item_id="test_item_id", request_id="req_exchange"
        )
        self.mock_api_client_instance.item_public_token_exchange.return_value = mock_exchange_response

        # 3. Mock transactions_get
        mock_tx = PlaidTransaction(transaction_id="tx1", date=date(2024,1,10), amount=10.50, name="Coffee Shop")
        mock_account = AccountBase(account_id="acc1", name="Checking", type="depository", subtype="checking")
        mock_transactions_response = TransactionsGetResponse(
            accounts=[mock_account], transactions=[mock_tx], total_transactions=1, item=MagicMock(), request_id="req_tx_get"
        )
        self.mock_api_client_instance.transactions_get.return_value = mock_transactions_response

        # Mock the csv.writer object itself to check writerow calls
        mock_writer_instance = MagicMock()
        mock_csv_writer.return_value = mock_writer_instance

        # Call the main function
        fetch_transactions(self.client_id, self.secret, output_file=self.output_file)

        # Assert Plaid client setup was done (implicitly by mock_plaid_api_factory being called)
        self.mock_plaid_api_factory.assert_called_once() 

        # Assert sandbox_public_token_create call
        self.mock_api_client_instance.sandbox_public_token_create.assert_called_once()
        # (Could add more detailed assertion for SandboxPublicTokenCreateRequest if needed)

        # Assert item_public_token_exchange call
        self.mock_api_client_instance.item_public_token_exchange.assert_called_once()
        exchange_request_arg = self.mock_api_client_instance.item_public_token_exchange.call_args[0][0]
        self.assertEqual(exchange_request_arg.public_token, "test_public_token")

        # Assert transactions_get call
        self.mock_api_client_instance.transactions_get.assert_called_once()
        tx_get_request_arg = self.mock_api_client_instance.transactions_get.call_args[0][0]
        self.assertEqual(tx_get_request_arg.access_token, "test_access_token_from_exchange")
        end_date = date.today() # fetch_transactions calculates this
        start_date = end_date - timedelta(days=30) # Default date range in script
        self.assertEqual(tx_get_request_arg.start_date, start_date)
        self.assertEqual(tx_get_request_arg.end_date, end_date)

        # Assert file open and CSV writing
        mock_open_file.assert_called_once_with(self.output_file, mode='w', newline='', encoding='utf-8')
        mock_csv_writer.assert_called_once_with(mock_open_file.return_value)
        
        expected_header = ['date', 'name', 'amount', 'transaction_id', 'account_id']
        mock_writer_instance.writerow.assert_any_call(expected_header)
        expected_row_data = [mock_tx.date, mock_tx.name, mock_tx.amount, mock_tx.transaction_id, mock_tx.account_id]
        mock_writer_instance.writerow.assert_any_call(expected_row_data)
        self.assertEqual(mock_writer_instance.writerow.call_count, 2) # Header + 1 transaction


    @patch('fetch_transactions.time.sleep')
    def test_fetch_transactions_retry_logic(self, mock_time_sleep):
        """Test retry logic on Plaid API errors like PRODUCT_NOT_READY."""
        # Mock token flow (successful)
        self.mock_api_client_instance.sandbox_public_token_create.return_value = SandboxPublicTokenCreateResponse(public_token="test_pt")
        self.mock_api_client_instance.item_public_token_exchange.return_value = ItemPublicTokenExchangeResponse(access_token="test_at")

        # Simulate PlaidError for PRODUCT_NOT_READY
        # The error string matching is `str(e)` contains 'PRODUCT_NOT_READY'
        class MockApiExceptionWithProductNotReady(ApiException):
            def __str__(self):
                return "API Error... PRODUCT_NOT_READY ..."

        api_exception_product_not_ready = MockApiExceptionWithProductNotReady(status=400, reason="Bad Request")
        
        mock_tx_response = TransactionsGetResponse(accounts=[], transactions=[], total_transactions=0)
        self.mock_api_client_instance.transactions_get.side_effect = [
            api_exception_product_not_ready, # 1st call fails
            api_exception_product_not_ready, # 2nd call fails
            mock_tx_response                 # 3rd call succeeds
        ]

        fetch_transactions(self.client_id, self.secret, self.output_file, 
                           max_retries=self.default_max_retries, delay=self.default_delay)

        self.assertEqual(self.mock_api_client_instance.transactions_get.call_count, 3)
        mock_time_sleep.assert_has_calls([call(self.default_delay), call(self.default_delay)])
        self.assertEqual(mock_time_sleep.call_count, 2)


    @patch('fetch_transactions.time.sleep')
    @patch('builtins.print')
    def test_fetch_transactions_retry_exhausted(self, mock_print, mock_time_sleep):
        """Test script failure message after exhausting retries."""
        self.mock_api_client_instance.sandbox_public_token_create.return_value = SandboxPublicTokenCreateResponse(public_token="test_pt")
        self.mock_api_client_instance.item_public_token_exchange.return_value = ItemPublicTokenExchangeResponse(access_token="test_at")

        class MockApiExceptionWithProductNotReady(ApiException):
            def __str__(self):
                return "API Error... PRODUCT_NOT_READY ..."
        api_exception = MockApiExceptionWithProductNotReady(status=400)
        
        self.mock_api_client_instance.transactions_get.side_effect = [api_exception] * (self.default_max_retries + 1)

        # The script's fetch_transactions catches the final exception and prints "Failed to fetch..."
        # then re-raises, which is caught by the outermost try-except in fetch_transactions.
        fetch_transactions(self.client_id, self.secret, self.output_file,
                           max_retries=self.default_max_retries, delay=self.default_delay)
        
        self.assertEqual(self.mock_api_client_instance.transactions_get.call_count, self.default_max_retries + 1)
        self.assertEqual(mock_time_sleep.call_count, self.default_max_retries)
        # Check for the "Failed to fetch transactions after multiple retries" message
        self.assertTrue(any("Failed to fetch transactions after multiple retries" in str(c[0]) for c in mock_print.call_args_list))
        # Also check for the final "Error fetching transactions:" message
        self.assertTrue(any("Error fetching transactions:" in str(c[0]) for c in mock_print.call_args_list))


    @patch('builtins.print')
    def test_fetch_transactions_api_error_other(self, mock_print):
        """Test handling of other Plaid API errors."""
        self.mock_api_client_instance.sandbox_public_token_create.return_value = SandboxPublicTokenCreateResponse(public_token="test_pt")
        self.mock_api_client_instance.item_public_token_exchange.return_value = ItemPublicTokenExchangeResponse(access_token="test_at")

        # Simulate a non-PRODUCT_NOT_READY ApiException
        other_api_exception = ApiException(status=500, reason="Internal Server Error", body=PlaidError("API_ERROR", "SERVER_ERROR", "Server error"))
        self.mock_api_client_instance.transactions_get.side_effect = other_api_exception

        fetch_transactions(self.client_id, self.secret, self.output_file)
        
        self.mock_api_client_instance.transactions_get.assert_called_once() # Called once, fails, no retry for this error type
        self.assertTrue(any("Error fetching transactions:" in str(c[0]) for c in mock_print.call_args_list))
        self.assertTrue(any("Internal Server Error" in str(c[0]) for c in mock_print.call_args_list))


    # --- Tests for __main__ entry point ---
    def run_main_with_args(self, args_list, mock_fetch_transactions_func):
        original_argv = sys.argv
        sys.argv = args_list
        
        # Path to the script to be exec'd. This assumes it's discoverable.
        script_path = "fetch_transactions.py" 
        
        try:
            with open(script_path, 'r') as f:
                script_code = f.read()
            
            # Prepare globals for exec. Mock the core function.
            exec_globals = {
                '__name__': '__main__',
                'sys': sys, # Patched sys for argv
                'fetch_transactions': mock_fetch_transactions_func, # Mock the core function
                # Add other necessary imports if script uses them directly in __main__ block
                # (fetch_transactions.py's __main__ only calls fetch_transactions and argparse)
            }
            exec(script_code, exec_globals)
        except SystemExit: # Catch SystemExit from argparse
            pass
        finally:
            sys.argv = original_argv

    @patch('fetch_transactions.fetch_transactions') # Mock the core function that __main__ calls
    def test_main_entry_success(self, mock_fetch_transactions_func):
        """Test __main__ entry point with required arguments, checking default parameters."""
        args = ["fetch_transactions.py", self.client_id, self.secret]
        self.run_main_with_args(args, mock_fetch_transactions_func)
        
        # Check that fetch_transactions was called with client_id, secret, and defaults
        # Defaults from fetch_transactions function signature in the script:
        # output_file="transactions.csv", max_retries=3, delay=1
        mock_fetch_transactions_func.assert_called_once_with(
            client_id=self.client_id,
            secret=self.secret,
            output_file="transactions.csv", # Default from function signature
            max_retries=3,                 # Default from function signature
            delay=1                        # Default from function signature
        )

    @patch('fetch_transactions.fetch_transactions') # Mock the core function
    @patch('builtins.print') # To capture argparse error output
    @patch('sys.exit')       # To prevent test runner from exiting
    def test_main_entry_insufficient_args(self, mock_sys_exit, mock_print, mock_fetch_transactions_func):
        """Test __main__ entry point with insufficient arguments."""
        args = ["fetch_transactions.py", self.client_id] # Missing secret
        self.run_main_with_args(args, mock_fetch_transactions_func)
        
        # Argparse should print usage and exit
        self.assertTrue(mock_print.called)
        # Check for a part of the usage message
        self.assertTrue(any("usage: fetch_transactions.py" in str(c[0][0]).lower() for c in mock_print.call_args_list if c[0]))
        mock_sys_exit.assert_called_once_with(1) # Argparse usually exits with 2, but script uses 1
        mock_fetch_transactions_func.assert_not_called()


if __name__ == '__main__':
    # Pre-patch Plaid modules if fetch_transactions.py imports them at top level
    mock_plaid_sdk_modules = {
        'plaid': MagicMock(),
        'plaid.api': MagicMock(),
        'plaid.model': MagicMock(), # Allow attribute access for models
        'plaid.exceptions': MagicMock(ApiException=ApiException),
        'plaid.model.plaid_error': MagicMock(PlaidError=PlaidError),
        'plaid.model.products': MagicMock(Products=Products),
        'plaid.model.country_code': MagicMock(CountryCode=CountryCode),
        'plaid.model.sandbox_public_token_create_response': MagicMock(SandboxPublicTokenCreateResponse=SandboxPublicTokenCreateResponse),
        'plaid.model.item_public_token_exchange_response': MagicMock(ItemPublicTokenExchangeResponse=ItemPublicTokenExchangeResponse),
        'plaid.model.transactions_get_response': MagicMock(TransactionsGetResponse=TransactionsGetResponse),
        'plaid.model.transaction': MagicMock(Transaction=PlaidTransaction), # Use alias
        'plaid.model.account_base': MagicMock(AccountBase=AccountBase),
        'plaid.model.item_public_token_create_request_options': MagicMock(ItemPublicTokenCreateRequestOptions=ItemPublicTokenCreateRequestOptions),
    }
    for module_name, mock_obj in mock_plaid_sdk_modules.items():
        if module_name not in sys.modules:
             sys.modules[module_name] = mock_obj
            
    unittest.main()
