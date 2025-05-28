import unittest
from unittest.mock import patch, MagicMock, call
import sys
import os
from datetime import datetime, timedelta
import time # Will be mocked

# Attempt to import from fetch_transactions.py
# If it doesn't exist, tests will use mocks.
try:
    from fetch_transactions import (
        create_plaid_client, # Assuming a helper function for client setup
        fetch_plaid_transactions, # Assuming this is the core logic function
        main as fetch_transactions_main # Assuming main entry point is named main
    )
    # Import Plaid specific exceptions if used for typed error handling
    from plaid.exceptions import ApiException 
    from plaid.model.plaid_error import PlaidError
    from plaid.model.products import Products
    from plaid.model.country_code import CountryCode
    # Models for mocking responses
    from plaid.model.transactions_get_response import TransactionsGetResponse
    from plaid.model.transaction import Transaction
    from plaid.model.account_base import AccountBase
    from plaid.model.item_public_token_exchange_response import ItemPublicTokenExchangeResponse # If this flow is used
except ImportError:
    print("Note: Could not import from fetch_transactions.py. Tests will proceed with mocks.")
    # Define dummy/mock classes if Plaid SDK is not available or script doesn't exist
    class ApiException(Exception):
        def __init__(self, status=None, reason=None, body=None, headers=None, link_code=None, error_type=None, error_code=None, display_message=None, causes=None):
            self.status = status
            self.reason = reason
            self.body = body # Often a PlaidError instance or dict
            self.headers = headers
            # PlaidError fields often in body
            self.link_code = link_code
            self.error_type = error_type
            self.error_code = error_code
            self.display_message = display_message
            self.causes = causes
            super().__init__(display_message or reason)

    class PlaidError: # Simplified mock
        def __init__(self, error_type, error_code, error_message, display_message=None, status_code=None):
            self.error_type = error_type
            self.error_code = error_code
            self.error_message = error_message
            self.display_message = display_message
            self.status_code = status_code
            self.causes = []
            self.request_id = "mock_request_id"

    class Products: # Enum-like mock
        TRANSACTIONS = "transactions"

    class CountryCode: # Enum-like mock
        US = "US"

    # Mock models for API responses
    class TransactionsGetResponse: pass
    class Transaction: pass
    class AccountBase: pass
    class ItemPublicTokenExchangeResponse: pass


    # Mock the functions if they couldn't be imported
    create_plaid_client = MagicMock()
    fetch_plaid_transactions = MagicMock()
    fetch_transactions_main = MagicMock()

# Mock pandas DataFrame and to_csv if pandas is not installed in test env
try:
    import pandas as pd
except ImportError:
    # Mock pandas DataFrame if not available
    class MockDataFrame:
        def __init__(self, data=None):
            self.data = data if data is not None else []
        def to_csv(self, path_or_buf, index=True):
            # print(f"MockDataFrame.to_csv called with path: {path_or_buf}")
            if hasattr(path_or_buf, 'write'):
                path_or_buf.write("mock,csv,data\n1,2,3")
            else:
                with open(path_or_buf, 'w') as f:
                    f.write("mock,csv,data\n1,2,3")
        def empty(self):
            return not self.data
            
    pd = MagicMock()
    pd.DataFrame = MockDataFrame


# Helper function to create a mock Plaid API client
def get_mock_plaid_api_client():
    mock_client = MagicMock()
    # Mock methods like transactions_get, item_public_token_exchange, etc.
    mock_client.transactions_get = MagicMock()
    mock_client.item_public_token_exchange = MagicMock() 
    # ... add other methods as needed based on fetch_transactions.py
    return mock_client

class TestFetchPlaidTransactions(unittest.TestCase):

    def setUp(self):
        self.client_id = "test_client_id"
        self.secret = "test_secret"
        self.access_token = "test_access_token" # Assuming script uses/obtains this
        self.output_file = "test_transactions.csv"
        self.max_retries = 3
        self.delay = 1

        # Mock Plaid API client setup
        self.mock_plaid_configuration = patch('fetch_transactions.plaid.Configuration').start()
        self.mock_plaid_api_client_constructor = patch('fetch_transactions.plaid.ApiClient').start()
        self.mock_plaid_api_factory = patch('fetch_transactions.plaid_api.PlaidApi').start() # If PlaidApi(api_client) pattern

        self.mock_api_client_instance = get_mock_plaid_api_client()
        self.mock_plaid_api_client_constructor.return_value = self.mock_api_client_instance # ApiClient() returns our mock
        self.mock_plaid_api_factory.return_value = self.mock_api_client_instance # PlaidApi(api_client) returns our mock

        # Stop patches during cleanup
        self.addCleanup(patch.stopall)


    def test_create_plaid_client_initialization(self):
        """Test Plaid API client initialization (if explicitly done)."""
        # This test assumes create_plaid_client is a function in fetch_transactions.py
        # that sets up and returns the PlaidApi instance.
        
        # Reset mocks for this specific test if create_plaid_client is called directly
        self.mock_plaid_configuration.reset_mock()
        self.mock_plaid_api_client_constructor.reset_mock()
        self.mock_plaid_api_factory.reset_mock()

        # Call the presumed client creation function
        # It should use PLAID_CLIENT_ID, PLAID_SECRET, PLAID_ENVIRONMENT from os.environ
        # or take them as args. Let's assume os.environ for now.
        with patch.dict(os.environ, {"PLAID_CLIENT_ID": self.client_id, 
                                     "PLAID_SECRET": self.secret, 
                                     "PLAID_ENVIRONMENT": "sandbox"}):
            client = create_plaid_client() # Or however it's called in the script

        self.mock_plaid_configuration.assert_called_once()
        args, kwargs = self.mock_plaid_configuration.call_args
        # Check host, api_key configuration
        self.assertIn('sandbox', str(kwargs.get('host')).lower()) # e.g. plaid.Environment.Sandbox
        self.assertTrue(any('PLAID_CLIENT_ID' in key for key in kwargs.get('api_key', {})))
        self.assertTrue(any('PLAID_SECRET' in key for key in kwargs.get('api_key', {})))
        
        self.mock_plaid_api_client_constructor.assert_called_once_with(self.mock_plaid_configuration.return_value)
        self.mock_plaid_api_factory.assert_called_once_with(self.mock_plaid_api_client_constructor.return_value)
        self.assertIsNotNone(client)


    @patch('fetch_transactions.pd.DataFrame') # Mock pandas DataFrame
    @patch('fetch_transactions.create_plaid_client') # Mock client creation
    def test_fetch_plaid_transactions_success(self, mock_create_client, mock_pd_dataframe):
        """Test successful fetching and processing of transactions."""
        mock_create_client.return_value = self.mock_api_client_instance
        
        # Mock Plaid API response for transactions_get
        mock_transaction = Transaction(transaction_id="tx1", date=datetime.now().date(), amount=10.0, name="Test Shop")
        mock_account = AccountBase(account_id="acc1", name="Checking", type="depository", subtype="checking")
        mock_transactions_response = TransactionsGetResponse(
            accounts=[mock_account],
            transactions=[mock_transaction],
            total_transactions=1,
            item=MagicMock(), # Mock item if needed
            request_id="req123"
        )
        self.mock_api_client_instance.transactions_get.return_value = mock_transactions_response

        # Mock DataFrame.to_csv
        mock_df_instance = mock_pd_dataframe.return_value
        mock_df_instance.to_csv = MagicMock()

        # Call the main fetching logic
        # Assuming fetch_plaid_transactions takes client_id, secret, and output_file
        # And that it internally handles access_token. For this test, let's assume it needs an access_token.
        # The actual script might get it from env or a file.
        # For now, let's assume fetch_plaid_transactions needs it as an arg, or it's globally managed.
        # If the script handles public_token_exchange, that needs to be mocked too.
        # For this test, let's assume access_token is directly available/passed.

        with patch.dict(os.environ, {"PLAID_ACCESS_TOKEN": self.access_token}): # If access token from env
            fetch_plaid_transactions(
                client_id=self.client_id, # Or these might be from env too
                secret=self.secret,
                output_file=self.output_file
                # date_range calculation is internal to fetch_plaid_transactions
            )

        # Verify transactions_get call
        self.mock_api_client_instance.transactions_get.assert_called_once()
        call_args, call_kwargs = self.mock_api_client_instance.transactions_get.call_args
        request_body = call_args[0] # TransactionsGetRequest is the first arg

        self.assertEqual(request_body.access_token, self.access_token)
        # Verify date range (last 10 days)
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=10) # As per README, last 10 days
        self.assertEqual(request_body.start_date, start_date)
        self.assertEqual(request_body.end_date, end_date)
        
        # Verify DataFrame creation and to_csv
        mock_pd_dataframe.assert_called_once() # Check data passed if possible
        mock_df_instance.to_csv.assert_called_once_with(self.output_file, index=False)


    @patch('fetch_transactions.time.sleep')
    @patch('fetch_transactions.create_plaid_client')
    def test_fetch_transactions_retry_logic(self, mock_create_client, mock_time_sleep):
        """Test retry logic on Plaid API errors like PRODUCT_NOT_READY."""
        mock_create_client.return_value = self.mock_api_client_instance

        # Simulate PlaidError for PRODUCT_NOT_READY
        plaid_error_body = PlaidError(
            error_type="ITEM_ERROR", 
            error_code="PRODUCT_NOT_READY", 
            error_message="Product not ready",
            display_message="Please try again later.",
            status_code=400 # Or whatever status Plaid uses for this
        )
        # ApiException body can be a dict or a PlaidError model instance
        api_exception_product_not_ready = ApiException(status=400, reason="Bad Request", body=plaid_error_body)

        mock_transactions_response = TransactionsGetResponse(accounts=[], transactions=[], total_transactions=0, item=MagicMock(), request_id="reqSuccess")
        
        self.mock_api_client_instance.transactions_get.side_effect = [
            api_exception_product_not_ready, # First call fails
            api_exception_product_not_ready, # Second call fails
            mock_transactions_response       # Third call succeeds
        ]

        with patch.dict(os.environ, {"PLAID_ACCESS_TOKEN": self.access_token}):
            fetch_plaid_transactions(
                client_id=self.client_id, secret=self.secret, output_file=self.output_file,
                max_retries=self.max_retries, delay=self.delay
            )

        self.assertEqual(self.mock_api_client_instance.transactions_get.call_count, 3)
        mock_time_sleep.assert_has_calls([call(self.delay), call(self.delay)])
        self.assertEqual(mock_time_sleep.call_count, 2)


    @patch('fetch_transactions.time.sleep')
    @patch('fetch_transactions.create_plaid_client')
    @patch('builtins.print') # To check for error messages
    def test_fetch_transactions_retry_exhausted(self, mock_print, mock_create_client, mock_time_sleep):
        """Test script failure after exhausting retries."""
        mock_create_client.return_value = self.mock_api_client_instance
        
        plaid_error_body = PlaidError("ITEM_ERROR", "PRODUCT_NOT_READY", "Product not ready")
        api_exception = ApiException(status=400, body=plaid_error_body)
        
        self.mock_api_client_instance.transactions_get.side_effect = [api_exception] * (self.max_retries + 1)

        with patch.dict(os.environ, {"PLAID_ACCESS_TOKEN": self.access_token}):
            with self.assertRaises(ApiException): # Assuming it re-raises the exception or a custom one
                 fetch_plaid_transactions(
                    client_id=self.client_id, secret=self.secret, output_file=self.output_file,
                    max_retries=self.max_retries, delay=self.delay
                )
        
        self.assertEqual(self.mock_api_client_instance.transactions_get.call_count, self.max_retries + 1)
        self.assertEqual(mock_time_sleep.call_count, self.max_retries)
        # Check for a message indicating retries exhausted
        self.assertTrue(any("Failed after" in str(c[0]) for c in mock_print.call_args_list))


    @patch('fetch_transactions.create_plaid_client')
    @patch('builtins.print')
    def test_plaid_api_authentication_error(self, mock_print, mock_create_client):
        """Test handling of Plaid API authentication errors."""
        mock_create_client.return_value = self.mock_api_client_instance
        
        auth_error_body = PlaidError("AUTH_ERROR", "INVALID_API_KEYS", "Invalid API keys")
        api_exception = ApiException(status=401, body=auth_error_body)
        self.mock_api_client_instance.transactions_get.side_effect = api_exception

        with patch.dict(os.environ, {"PLAID_ACCESS_TOKEN": self.access_token}):
            with self.assertRaises(ApiException): # Or check for sys.exit(1) if it exits
                fetch_plaid_transactions(client_id=self.client_id, secret=self.secret, output_file=self.output_file)
        
        # Check for specific error print related to authentication
        self.assertTrue(any("Authentication error" in str(c[0]) or "INVALID_API_KEYS" in str(c[0]) for c in mock_print.call_args_list))


    # --- Tests for main entry point ---
    @patch('fetch_transactions.fetch_plaid_transactions') # Mock the core function
    def run_main_with_args(self, args_list, mock_fetch_func):
        """Helper to run the main part of the script with mocked sys.argv."""
        original_argv = sys.argv
        sys.argv = args_list
        try:
            # This assumes fetch_transactions.py has a main() function that is called
            # when the script is run.
            fetch_transactions_main() # Call the aliased main
        except SystemExit: # Catch sys.exit from argparse
            pass 
        finally:
            sys.argv = original_argv

    @patch('fetch_transactions.fetch_plaid_transactions')
    def test_main_entry_required_args(self, mock_fetch_transactions_func):
        """Test main entry point with only required arguments."""
        args = ["fetch_transactions.py", self.client_id, self.secret]
        self.run_main_with_args(args, mock_fetch_transactions_func)
        
        # Default values for output_file, max_retries, delay should be used
        # These defaults need to be known from fetch_transactions.py's argparse setup
        # Assuming defaults: output_file='transactions.csv', max_retries=3, delay=1
        expected_output_file = 'transactions.csv' 
        expected_max_retries = 3
        expected_delay = 1
        
        mock_fetch_transactions_func.assert_called_once_with(
            client_id=self.client_id,
            secret=self.secret,
            output_file=expected_output_file,
            max_retries=expected_max_retries,
            delay=expected_delay
        )

    @patch('fetch_transactions.fetch_plaid_transactions')
    def test_main_entry_all_args(self, mock_fetch_transactions_func):
        """Test main entry point with all arguments specified."""
        custom_output = "custom.csv"
        custom_retries = 5
        custom_delay = 2
        args = [
            "fetch_transactions.py", self.client_id, self.secret,
            "--output_file", custom_output,
            "--max_retries", str(custom_retries),
            "--delay", str(custom_delay)
        ]
        self.run_main_with_args(args, mock_fetch_transactions_func)
        mock_fetch_transactions_func.assert_called_once_with(
            client_id=self.client_id,
            secret=self.secret,
            output_file=custom_output,
            max_retries=custom_retries,
            delay=custom_delay
        )

    @patch('fetch_transactions.fetch_plaid_transactions') # Won't be called
    @patch('builtins.print') # To capture argparse error output
    @patch('sys.exit') # To prevent test runner from exiting
    def test_main_entry_missing_arguments(self, mock_sys_exit, mock_print, mock_fetch_transactions_func):
        """Test main entry point with missing required arguments."""
        args = ["fetch_transactions.py", self.client_id] # Missing secret
        self.run_main_with_args(args, mock_fetch_transactions_func)
        
        # argparse should print an error and exit
        self.assertTrue(mock_print.called or mock_sys_exit.called)
        # Check that the error message indicates missing arguments
        # Example: self.assertTrue(any("the following arguments are required: secret" in str(c[0]) for c in mock_print.call_args_list))
        mock_fetch_transactions_func.assert_not_called()


if __name__ == '__main__':
    # Pre-patch Plaid modules if fetch_transactions.py imports them at top level
    # This is to prevent import errors if the Plaid SDK isn't fully available
    # or if the script expects configuration at import time.
    mock_plaid = MagicMock()
    sys.modules['plaid'] = mock_plaid
    sys.modules['plaid.api'] = MagicMock()
    sys.modules['plaid.model'] = MagicMock()
    sys.modules['plaid.exceptions'] = MagicMock(ApiException=ApiException)
    sys.modules['plaid.model.plaid_error'] = MagicMock(PlaidError=PlaidError)
    sys.modules['plaid.model.products'] = MagicMock(Products=Products)
    sys.modules['plaid.model.country_code'] = MagicMock(CountryCode=CountryCode)
    sys.modules['plaid.model.transactions_get_response'] = MagicMock(TransactionsGetResponse=TransactionsGetResponse)
    sys.modules['plaid.model.transaction'] = MagicMock(Transaction=Transaction)
    sys.modules['plaid.model.account_base'] = MagicMock(AccountBase=AccountBase)
    sys.modules['plaid.model.item_public_token_exchange_response'] = MagicMock(ItemPublicTokenExchangeResponse=ItemPublicTokenExchangeResponse)
    
    # Mock pandas if not installed
    if 'pd' not in sys.modules:
         sys.modules['pandas'] = pd # Our mocked pd (MagicMock or MockDataFrame holder)
    
    unittest.main()
