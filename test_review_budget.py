import unittest
from unittest.mock import patch, MagicMock, call, mock_open
import sys
import os
from datetime import datetime, timedelta
import io

# Attempt to import from review_budget.py
# If it doesn't exist, tests will use mocks.
try:
    from review_budget import (
        get_last_two_months_files, # Corrected
        concatenate_transactions,    # Corrected
        analyze_transactions,      # Corrected
        main as review_budget_main
    )
    # Import OpenAI specific exceptions if used for typed error handling
    from openai import OpenAI, APIError, AuthenticationError, RateLimitError 
except ImportError:
    print("Note: Could not import from review_budget.py. Tests will proceed with mocks.")
    class APIError(Exception): pass
    class AuthenticationError(Exception): pass
    class RateLimitError(Exception): pass
    
    class MockOpenAIClient:
        def __init__(self, api_key=None):
            self.api_key = api_key
            self.chat = MagicMock()
            self.chat.completions = MagicMock()
            self.chat.completions.create = MagicMock()
    
    OpenAI = MockOpenAIClient

    # Mock the functions if they couldn't be imported - Corrected names
    get_last_two_months_files = MagicMock()
    concatenate_transactions = MagicMock()
    analyze_transactions = MagicMock()
    review_budget_main = MagicMock()

# Mock pandas DataFrame
try:
    import pandas as pd
except ImportError:
    class MockDataFrame:
        def __init__(self, data=None):
            self.data = data if data is not None else []
        def to_csv(self, path_or_buf=None, index=True, header=True):
            content = "mock_col1,mock_col2\n" if header else ""
            for row_idx, row in enumerate(self.data): # Handle list of lists or list of dicts
                if isinstance(row, dict):
                    if row_idx == 0 and header: # Construct header from keys if not provided
                         content = ",".join(row.keys()) + "\n"
                    content += ",".join(map(str, row.values())) + "\n"
                else: # Assume list of lists
                    content += ",".join(map(str, row)) + "\n"

            if path_or_buf and hasattr(path_or_buf, 'write'):
                path_or_buf.write(content)
            elif path_or_buf:
                with open(path_or_buf, 'w') as f:
                    f.write(content)
            return content if path_or_buf is None else None

        def empty(self):
            return not bool(self.data)
        
        @staticmethod
        def concat(dfs, ignore_index=False): # Added ignore_index
            all_data = []
            for df_mock in dfs:
                if not df_mock.empty():
                    all_data.extend(df_mock.data)
            return MockDataFrame(all_data)

    pd = MagicMock()
    pd.DataFrame = MockDataFrame
    pd.concat = MockDataFrame.concat
    pd.read_csv = MagicMock(return_value=MockDataFrame([["r1c1","r1c2"],["r2c1","r2c2"]]))


class TestReviewBudget(unittest.TestCase):

    def setUp(self):
        self.folder_path = "test_transactions_folder"
        self.budget = 1000.0
        self.api_key = "test_openai_api_key"
        self.mock_openai_client_instance = OpenAI(api_key=self.api_key)

    # --- Tests for get_last_two_months_files ---
    @patch('review_budget.datetime') # Mock datetime within the review_budget module
    def test_get_last_two_months_files_success(self, mock_datetime): # Removed os.listdir mock
        """Test getting file paths for the last two months."""
        # Simulate current date: March 15, 2024
        mock_datetime.now.return_value = datetime(2024, 3, 15)
        # Allow datetime constructor to work normally for timedelta etc.
        mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs) if args else datetime.now()


        expected_file_1 = os.path.join(self.folder_path, "February 2024 - transactions.csv") # Prev month
        expected_file_2 = os.path.join(self.folder_path, "January 2024 - transactions.csv") # Prev-prev month
        
        # get_last_two_months_files returns (prev_month_file, prev_prev_month_file)
        actual_file_1, actual_file_2 = get_last_two_months_files(self.folder_path)
        
        self.assertEqual(expected_file_1, actual_file_1)
        self.assertEqual(expected_file_2, actual_file_2)

    @patch('review_budget.datetime')
    def test_get_last_two_months_files_no_problem_if_files_dont_exist_yet(self, mock_datetime):
        """Test that get_last_two_months_files returns paths even if files don't physically exist."""
        mock_datetime.now.return_value = datetime(2024, 1, 10) # January 2024
        mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs) if args else datetime.now()

        # Expected: December 2023, November 2023
        expected_dec_file = os.path.join(self.folder_path, "December 2023 - transactions.csv")
        expected_nov_file = os.path.join(self.folder_path, "November 2023 - transactions.csv")

        file1, file2 = get_last_two_months_files(self.folder_path)
        self.assertEqual(file1, expected_dec_file)
        self.assertEqual(file2, expected_nov_file)
        # No os.path.exists or listdir checks are done by get_last_two_months_files itself.

    # test_find_transaction_files_folder_not_exist: Removed as get_last_two_months_files doesn't check folder existence.

    # --- Tests for concatenate_transactions ---
    @patch('review_budget.get_last_two_months_files')
    @patch('review_budget.os.path.exists')
    @patch('review_budget.pd.read_csv')
    @patch('review_budget.pd.concat')
    @patch('review_budget.open', new_callable=mock_open) # Mock for output CSV writing
    def test_concatenate_transactions_success(self, mock_file_open, mock_pd_concat, mock_pd_read_csv, 
                                             mock_os_exists, mock_get_last_two_months):
        """Test successful loading and combination of CSVs determined by get_last_two_months_files."""
        mock_file1_path = os.path.join(self.folder_path, "mock_month1_transactions.csv")
        mock_file2_path = os.path.join(self.folder_path, "mock_month2_transactions.csv")
        
        mock_get_last_two_months.return_value = (mock_file1_path, mock_file2_path)
        mock_os_exists.return_value = True # Both input files exist

        mock_df1_data = [{'colA': 1, 'colB': 'data1'}]
        mock_df2_data = [{'colA': 2, 'colB': 'data2'}]
        mock_df1 = pd.DataFrame(mock_df1_data) # Using our mock DataFrame
        mock_df2 = pd.DataFrame(mock_df2_data)
        mock_pd_read_csv.side_effect = [mock_df1, mock_df2]
        
        mock_combined_df_data = mock_df1_data + mock_df2_data
        mock_combined_df = pd.DataFrame(mock_combined_df_data)
        mock_pd_concat.return_value = mock_combined_df

        result_df = concatenate_transactions(self.folder_path)

        mock_get_last_two_months.assert_called_once_with(self.folder_path)
        mock_os_exists.assert_has_calls([call(mock_file1_path), call(mock_file2_path)], any_order=True)
        mock_pd_read_csv.assert_has_calls([call(mock_file1_path), call(mock_file2_path)], any_order=True)
        mock_pd_concat.assert_called_once_with([mock_df1, mock_df2], ignore_index=True)
        self.assertFalse(result_df.empty())
        
        # Check if combined CSV was written (concatenate_transactions writes to 'combined_transactions.csv')
        # The path for combined_transactions.csv needs to be determined based on review_budget.py logic
        # Assuming it's in self.folder_path for now.
        expected_output_csv_path = os.path.join(self.folder_path, "combined_transactions.csv")
        mock_file_open.assert_called_once_with(expected_output_csv_path, 'w', newline='', encoding='utf-8')
        # Check if to_csv was called on the combined_df (which is mock_pd_concat.return_value)
        mock_pd_concat.return_value.to_csv.assert_called_once_with(mock_file_open.return_value, index=False)


    # test_load_and_combine_empty_file_list: Removed as not applicable.

    @patch('review_budget.get_last_two_months_files')
    @patch('review_budget.os.path.exists')
    @patch('review_budget.pd.read_csv')
    @patch('review_budget.sys.exit') # Mock sys.exit
    @patch('builtins.print') 
    def test_concatenate_transactions_malformed_csv(self, mock_print, mock_sys_exit, mock_pd_read_csv, 
                                                 mock_os_exists, mock_get_last_two_months):
        """Test behavior when a CSV is malformed during concatenation."""
        mock_file1_path = os.path.join(self.folder_path, "good.csv")
        mock_file2_path = os.path.join(self.folder_path, "bad.csv")
        
        mock_get_last_two_months.return_value = (mock_file1_path, mock_file2_path)
        mock_os_exists.return_value = True # Both files exist initially

        mock_good_df = pd.DataFrame([{'colA': 1}])
        # Simulate read_csv failing for the second file
        mock_pd_read_csv.side_effect = [mock_good_df, pd.errors.EmptyDataError("Error parsing bad.csv")] 
                                        # Or any other pandas parsing error

        # The script review_budget.py's concatenate_transactions has a try-except for pd.read_csv
        # that prints an error and re-raises the exception if it's not FileNotFoundError.
        # So, we expect an exception here.
        with self.assertRaises(pd.errors.EmptyDataError): # Or the specific exception you expect
            concatenate_transactions(self.folder_path)
        
        mock_get_last_two_months.assert_called_once_with(self.folder_path)
        # os.path.exists called for both, then pd.read_csv for both (second one fails)
        mock_os_exists.assert_has_calls([call(mock_file1_path), call(mock_file2_path)], any_order=True)
        mock_pd_read_csv.assert_has_calls([call(mock_file1_path), call(mock_file2_path)], any_order=True)
        mock_print.assert_any_call(f"Error reading or processing file {mock_file2_path}: Error parsing bad.csv")
        mock_sys_exit.assert_not_called() # Should not be called if error is pd.errors.EmptyDataError

    @patch('review_budget.get_last_two_months_files')
    @patch('review_budget.os.path.exists')
    @patch('review_budget.sys.exit') # Mock sys.exit
    @patch('builtins.print')
    def test_concatenate_transactions_input_file_not_found(self, mock_print, mock_sys_exit, mock_os_exists, mock_get_last_two_months):
        """Test concatenate_transactions when an input CSV file doesn't exist."""
        mock_file1_path = os.path.join(self.folder_path, "exists.csv")
        mock_file2_path = os.path.join(self.folder_path, "missing.csv")
        
        mock_get_last_two_months.return_value = (mock_file1_path, mock_file2_path)
        # Simulate first file exists, second does not
        mock_os_exists.side_effect = lambda path: True if path == mock_file1_path else False

        concatenate_transactions(self.folder_path)
        
        mock_print.assert_any_call(f"Error: Transaction file {mock_file2_path} not found.")
        mock_sys_exit.assert_called_once_with(1)


    # --- Tests for analyze_transactions --- (formerly get_financial_analysis)
    @patch('review_budget.OpenAI') 
    def test_analyze_transactions_success(self, mock_openai_constructor): # Renamed
        """Test successful financial analysis from OpenAI."""
        mock_client = self.mock_openai_client_instance
        mock_openai_constructor.return_value = mock_client
        
        sample_analysis_text = "Your spending is optimal."
        mock_chat_completion = MagicMock()
        mock_chat_completion.choices = [MagicMock(message=MagicMock(content=sample_analysis_text))]
        mock_client.chat.completions.create.return_value = mock_chat_completion

        transactions_data = [{'date': '2024-01-05', 'description': 'Coffee', 'amount': -5.00}]
        transactions_df = pd.DataFrame(transactions_data)
        
        transactions_str_summary = transactions_df.to_csv(path_or_buf=None, index=False, header=True) 

        analysis = analyze_transactions(transactions_df, self.budget, self.api_key) # Renamed call

        mock_openai_constructor.assert_called_once_with(api_key=self.api_key)
        mock_client.chat.completions.create.assert_called_once()
        
        args, kwargs = mock_client.chat.completions.create.call_args
        prompt_messages = kwargs['messages']
        self.assertIn(str(self.budget), prompt_messages[-1]['content'])
        # Check for parts of the CSV string. Using [:100] to avoid issues with full large CSV string comparison
        self.assertIn(transactions_str_summary[:100], prompt_messages[-1]['content']) 
        
        self.assertEqual(analysis, sample_analysis_text)

    @patch('review_budget.OpenAI')
    @patch('builtins.print')
    def test_analyze_transactions_openai_api_error(self, mock_print, mock_openai_constructor): # Renamed
        mock_client = self.mock_openai_client_instance
        mock_openai_constructor.return_value = mock_client
        mock_client.chat.completions.create.side_effect = APIError("Mock API Error", request=None, body=None) # Corrected from previous

        transactions_df = pd.DataFrame([{'desc': 'tx1', 'amount': 10}])
        analysis = analyze_transactions(transactions_df, self.budget, self.api_key) # Renamed call

        self.assertIsNone(analysis) 
        mock_print.assert_any_call("OpenAI API Error: Mock API Error") # Check for specific error message

    # --- Tests for main entry point ---
    # Updated mock names in the helper and tests below
    @patch('review_budget.get_last_two_months_files') # Corrected
    @patch('review_budget.concatenate_transactions')    # Corrected
    @patch('review_budget.analyze_transactions')      # Corrected
    @patch('builtins.print') 
    def run_main_with_mocks(self, args_list, mock_print, mock_analyze_transactions, 
                           mock_concatenate_transactions, mock_get_last_two_months): # Corrected mock names
        """Helper to run main with patched sys.argv and mocked functions."""
        
        mock_get_last_two_months.return_value = (os.path.join(self.folder_path,"file1.csv"), os.path.join(self.folder_path,"file2.csv"))
        mock_transactions_df = pd.DataFrame([{'amount': 100}])
        mock_concatenate_transactions.return_value = mock_transactions_df # concatenate_transactions returns the DataFrame
        mock_analyze_transactions.return_value = "This is your financial analysis."

        original_argv = sys.argv
        sys.argv = args_list
        try:
            review_budget_main() 
        except SystemExit: 
            pass
        finally:
            sys.argv = original_argv

    @patch('review_budget.get_last_two_months_files') # Corrected
    @patch('review_budget.concatenate_transactions')    # Corrected
    @patch('review_budget.analyze_transactions')      # Corrected
    @patch('builtins.print')
    def test_main_success_flow(self, mock_print, mock_analyze_transactions, 
                              mock_concatenate_transactions, mock_get_last_two_months): # Corrected mock names
        """Test the main script flow for a successful case."""
        args = ["review_budget.py", self.folder_path, str(self.budget), self.api_key]
        self.run_main_with_mocks(args, mock_print, mock_analyze_transactions, 
                                 mock_concatenate_transactions, mock_get_last_two_months) # Corrected call

        mock_get_last_two_months.assert_called_once_with(self.folder_path) # This is called by concatenate_transactions now
                                                                          # So concatenate_transactions should be the direct mock if main calls it
        # If main calls concatenate_transactions directly, then get_last_two_months_files is not directly called by main.
        # Let's assume main calls concatenate_transactions, which then calls get_last_two_months_files.
        # The test for main should then primarily mock concatenate_transactions.
        # For this test structure, let's assume main calls concatenate_transactions,
        # and concatenate_transactions is well-tested elsewhere for its internal calls.
        
        mock_concatenate_transactions.assert_called_once_with(self.folder_path)
        loaded_df = mock_concatenate_transactions.return_value # This is the combined DataFrame
        mock_analyze_transactions.assert_called_once_with(loaded_df, self.budget, self.api_key)
        self.assertTrue(any(mock_analyze_transactions.return_value in str(c[0]) for c in mock_print.call_args_list))

    @patch('review_budget.concatenate_transactions') # Mock concatenate directly
    @patch('review_budget.analyze_transactions')      
    @patch('review_budget.sys.exit') # To check if sys.exit is called
    @patch('builtins.print')
    def test_main_concatenate_fails_or_returns_empty(self, mock_print, mock_sys_exit,
                                               mock_analyze_transactions, mock_concatenate_transactions):
        """Test main flow when concatenate_transactions fails or returns empty DataFrame."""
        # Scenario 1: concatenate_transactions returns an empty DataFrame (e.g., if input files were empty, not missing)
        mock_empty_df = pd.DataFrame([])
        mock_concatenate_transactions.return_value = mock_empty_df

        args = ["review_budget.py", self.folder_path, str(self.budget), self.api_key]
        self.run_main_with_mocks(args, mock_print, mock_analyze_transactions, 
                                 mock_concatenate_transactions, MagicMock()) # Pass a dummy for get_last_two_months for the helper

        mock_concatenate_transactions.assert_called_once_with(self.folder_path)
        mock_analyze_transactions.assert_not_called() # Should not be called if DF is empty
        mock_print.assert_any_call("No transaction data to analyze after concatenation.")
        mock_sys_exit.assert_called_once_with(1) # Expect sys.exit(1)

        # Scenario 2: concatenate_transactions itself raises an exception (e.g. due to file not found, handled by sys.exit there)
        # This is implicitly tested by test_concatenate_transactions_input_file_not_found for concatenate_transactions
        # If main calls it, and it sys.exits, then main stops.
        mock_concatenate_transactions.reset_mock()
        mock_sys_exit.reset_mock()
        mock_print.reset_mock()
        mock_analyze_transactions.reset_mock()

        mock_concatenate_transactions.side_effect = SystemExit(1) # Simulate sys.exit from within
        
        # We expect SystemExit to propagate if not caught by main, or for main to handle it.
        # The helper run_main_with_mocks catches SystemExit.
        self.run_main_with_mocks(args, mock_print, mock_analyze_transactions, 
                                 mock_concatenate_transactions, MagicMock())
        
        mock_concatenate_transactions.assert_called_once_with(self.folder_path)
        mock_analyze_transactions.assert_not_called()
        # sys.exit was called from within the mocked function, so the helper's sys.exit catch handles it.
        # No direct mock_sys_exit.assert_called_once_with(1) here as it's part of the side_effect.


    @patch('review_budget.concatenate_transactions') # Other mocks not strictly needed as argparse exits
    @patch('builtins.print')
    @patch('sys.exit')
    def test_main_missing_arguments(self, mock_sys_exit, mock_print, mock_concatenate_transactions_unused):
        """Test main with missing required arguments."""
        args = ["review_budget.py", self.folder_path] # Missing budget and api_key
        # Use the main helper, but some mocks are not relevant as argparse will fail first
        self.run_main_with_mocks(args, mock_print, MagicMock(), 
                                 mock_concatenate_transactions_unused, MagicMock())
        
        self.assertTrue(mock_print.called or mock_sys_exit.called)
        mock_concatenate_transactions_unused.assert_not_called()

    @patch('review_budget.concatenate_transactions')
    @patch('builtins.print')
    @patch('sys.exit')
    def test_main_invalid_budget_argument(self, mock_sys_exit, mock_print, mock_concatenate_transactions_unused):
        """Test main with a non-numeric budget argument."""
        args = ["review_budget.py", self.folder_path, "not_a_number", self.api_key]
        self.run_main_with_mocks(args, mock_print, MagicMock(), 
                                 mock_concatenate_transactions_unused, MagicMock())

        self.assertTrue(mock_print.called or mock_sys_exit.called)

if __name__ == '__main__':
    if 'openai' not in sys.modules: 
        sys.modules['openai'] = MagicMock(OpenAI=OpenAI, APIError=APIError, 
                                          AuthenticationError=AuthenticationError, RateLimitError=RateLimitError)
    if 'pd' not in sys.modules:
         sys.modules['pandas'] = pd
            
    unittest.main()
