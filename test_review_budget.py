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
        find_transaction_files,
        load_and_combine_transactions,
        get_financial_analysis,
        main as review_budget_main
    )
    # Import OpenAI specific exceptions if used for typed error handling
    # Assuming newer OpenAI SDK (v1.x.x)
    from openai import OpenAI, APIError, AuthenticationError, RateLimitError 
except ImportError:
    print("Note: Could not import from review_budget.py. Tests will proceed with mocks.")
    # Define dummy/mock classes if OpenAI SDK is not available or script doesn't exist
    class APIError(Exception): pass
    class AuthenticationError(Exception): pass
    class RateLimitError(Exception): pass
    
    # Mock for OpenAI client if SDK not present
    class MockOpenAIClient:
        def __init__(self, api_key=None):
            self.api_key = api_key
            self.chat = MagicMock()
            self.chat.completions = MagicMock()
            self.chat.completions.create = MagicMock()
    
    OpenAI = MockOpenAIClient # Use our mock if actual OpenAI not available

    # Mock the functions if they couldn't be imported
    find_transaction_files = MagicMock()
    load_and_combine_transactions = MagicMock()
    get_financial_analysis = MagicMock()
    review_budget_main = MagicMock()

# Mock pandas DataFrame and to_csv if pandas is not installed in test env
try:
    import pandas as pd
except ImportError:
    class MockDataFrame:
        def __init__(self, data=None):
            self.data = data if data is not None else []
        def to_csv(self, path_or_buf=None, index=True, header=True): # Added header
            content = "mock_col1,mock_col2\n" if header else ""
            for row in self.data:
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
        def concat(dfs):
            all_data = []
            for df_mock in dfs:
                if not df_mock.empty():
                    all_data.extend(df_mock.data)
            return MockDataFrame(all_data)

    pd = MagicMock()
    pd.DataFrame = MockDataFrame
    pd.concat = MockDataFrame.concat # Static method for concat
    pd.read_csv = MagicMock(return_value=MockDataFrame([["r1c1","r1c2"],["r2c1","r2c2"]]))


class TestReviewBudget(unittest.TestCase):

    def setUp(self):
        self.folder_path = "test_transactions_folder"
        self.budget = 1000.0
        self.api_key = "test_openai_api_key"
        self.mock_openai_client_instance = OpenAI(api_key=self.api_key) # Used if OpenAI is our mock

    # --- Tests for find_transaction_files ---
    @patch('review_budget.os.path.exists')
    @patch('review_budget.os.listdir')
    @patch('review_budget.datetime') # Mock datetime within the review_budget module
    def test_find_transaction_files_success(self, mock_datetime, mock_listdir, mock_os_exists):
        """Test finding transaction files for the last two months."""
        mock_os_exists.return_value = True # Folder exists
        
        # Simulate current date: March 15, 2024
        # Expected files: February 2024, January 2024
        mock_datetime.now.return_value = datetime(2024, 3, 15)
        mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs) # Allow datetime constructor

        all_files = [
            "January 2024 - transactions.csv",
            "February 2024 - transactions.csv",
            "December 2023 - transactions.csv", # Should be ignored
            "March 2024 - transactions.csv",    # Should be ignored (current month, not "last two")
            "February 2024 - other_doc.txt",    # Should be ignored
            "random_file.csv"                   # Should be ignored
        ]
        mock_listdir.return_value = all_files

        expected_files = [
            os.path.join(self.folder_path, "January 2024 - transactions.csv"),
            os.path.join(self.folder_path, "February 2024 - transactions.csv")
        ]
        
        # Sorting expected and actual results because os.listdir order is not guaranteed
        actual_files = sorted(find_transaction_files(self.folder_path))
        
        mock_os_exists.assert_called_once_with(self.folder_path)
        mock_listdir.assert_called_once_with(self.folder_path)
        self.assertEqual(sorted(expected_files), actual_files)

    @patch('review_budget.os.path.exists')
    @patch('review_budget.os.listdir')
    @patch('review_budget.datetime')
    def test_find_transaction_files_no_matches(self, mock_datetime, mock_listdir, mock_os_exists):
        mock_os_exists.return_value = True
        mock_datetime.now.return_value = datetime(2024, 3, 15)
        mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)
        mock_listdir.return_value = ["December 2023 - transactions.csv", "random.txt"]

        self.assertEqual(find_transaction_files(self.folder_path), [])

    @patch('review_budget.os.path.exists', return_value=False)
    @patch('builtins.print') # If it prints an error
    def test_find_transaction_files_folder_not_exist(self, mock_print, mock_os_exists):
        # Depending on implementation: could raise error or return empty list and print
        result = find_transaction_files(self.folder_path)
        self.assertEqual(result, []) # Assuming it returns empty list
        # mock_print.assert_any_call(f"Error: Folder '{self.folder_path}' not found.") # If it prints
        mock_os_exists.assert_called_once_with(self.folder_path)


    # --- Tests for load_and_combine_transactions ---
    @patch('review_budget.pd.read_csv')
    @patch('review_budget.pd.concat')
    def test_load_and_combine_success(self, mock_pd_concat, mock_pd_read_csv):
        """Test successful loading and combination of CSVs."""
        file_paths = ["path/to/file1.csv", "path/to/file2.csv"]
        mock_df1 = pd.DataFrame([{'colA': 1, 'colB': 'data1'}])
        mock_df2 = pd.DataFrame([{'colA': 2, 'colB': 'data2'}])
        mock_pd_read_csv.side_effect = [mock_df1, mock_df2]
        
        mock_combined_df = pd.DataFrame([{'colA': 1, 'colB': 'data1'}, {'colA': 2, 'colB': 'data2'}])
        mock_pd_concat.return_value = mock_combined_df

        result_df = load_and_combine_transactions(file_paths)

        mock_pd_read_csv.assert_has_calls([call("path/to/file1.csv"), call("path/to/file2.csv")])
        mock_pd_concat.assert_called_once_with([mock_df1, mock_df2], ignore_index=True)
        self.assertFalse(result_df.empty()) # Using our mock DataFrame's empty method
        # Potentially: pd.testing.assert_frame_equal(result_df, mock_combined_df) if using real pandas

    def test_load_and_combine_empty_file_list(self):
        """Test with an empty list of file paths."""
        result_df = load_and_combine_transactions([])
        self.assertTrue(result_df.empty()) # Should return an empty DataFrame


    @patch('review_budget.pd.read_csv', side_effect=Exception("CSV parsing error"))
    @patch('builtins.print') # If it prints an error for malformed CSV
    def test_load_and_combine_malformed_csv(self, mock_print, mock_pd_read_csv):
        """Test behavior when a CSV is malformed."""
        file_paths = ["path/to/good.csv", "path/to/bad.csv"]
        
        # First read_csv is good, second raises error
        mock_good_df = pd.DataFrame([{'colA': 1}])
        mock_pd_read_csv.side_effect = [mock_good_df, Exception("CSV parsing error for bad.csv")]

        # Assuming the function logs the error and continues, possibly skipping the bad file
        # or returns an empty/partial DataFrame. Let's assume it skips and continues.
        # If it's designed to fail completely, then assertRaises.
        
        # This depends on the error handling in load_and_combine_transactions
        # For now, assume it tries to load all, and if one fails, it might be skipped
        # or the whole operation might fail. If it skips:
        with patch('review_budget.pd.concat') as mock_pd_concat:
            mock_pd_concat.return_value = mock_good_df # Only good_df was concatenated
            result_df = load_and_combine_transactions(file_paths)
            mock_print.assert_any_call(unittest.mock.ANY) # Check if error for bad.csv was printed
            mock_pd_concat.assert_called_once_with([mock_good_df], ignore_index=True) # Only good_df passed to concat
            self.assertFalse(result_df.empty())

    # --- Tests for get_financial_analysis ---
    @patch('review_budget.OpenAI') # Mock the OpenAI client constructor
    def test_get_financial_analysis_success(self, mock_openai_constructor):
        """Test successful financial analysis from OpenAI."""
        mock_client = self.mock_openai_client_instance # Use our pre-configured mock client
        mock_openai_constructor.return_value = mock_client
        
        sample_analysis_text = "Your spending is optimal."
        mock_chat_completion = MagicMock()
        mock_chat_completion.choices = [MagicMock(message=MagicMock(content=sample_analysis_text))]
        mock_client.chat.completions.create.return_value = mock_chat_completion

        transactions_data = [{'date': '2024-01-05', 'description': 'Coffee', 'amount': -5.00}]
        transactions_df = pd.DataFrame(transactions_data) # Using our mock DataFrame
        
        # Convert DataFrame to string as it might be in the prompt
        # The exact format depends on review_budget.py
        transactions_str_summary = transactions_df.to_csv(index=False, header=True) 

        analysis = get_financial_analysis(transactions_df, self.budget, self.api_key)

        mock_openai_constructor.assert_called_once_with(api_key=self.api_key)
        mock_client.chat.completions.create.assert_called_once()
        
        # Check prompt construction (this is highly dependent on the actual prompt)
        args, kwargs = mock_client.chat.completions.create.call_args
        prompt_messages = kwargs['messages']
        # Assuming system prompt and user prompt with data
        self.assertIn(str(self.budget), prompt_messages[-1]['content'])
        self.assertIn(transactions_str_summary[:50], prompt_messages[-1]['content']) # Check part of CSV string
        
        self.assertEqual(analysis, sample_analysis_text)

    @patch('review_budget.OpenAI')
    @patch('builtins.print')
    def test_get_financial_analysis_openai_api_error(self, mock_print, mock_openai_constructor):
        mock_client = self.mock_openai_client_instance
        mock_openai_constructor.return_value = mock_client
        mock_client.chat.completions.create.side_effect = APIError("Mock API Error", request=None, body=None)

        transactions_df = pd.DataFrame([{'desc': 'tx1', 'amount': 10}])
        analysis = get_financial_analysis(transactions_df, self.budget, self.api_key)

        self.assertIsNone(analysis) # Or check for specific error message return
        mock_print.assert_any_call(unittest.mock.ANY) # Check if error was printed

    # --- Tests for main entry point ---
    @patch('review_budget.find_transaction_files')
    @patch('review_budget.load_and_combine_transactions')
    @patch('review_budget.get_financial_analysis')
    @patch('builtins.print') # To capture final output
    def run_main_with_mocks(self, args_list, mock_print, mock_get_analysis, mock_load_combine, mock_find_files):
        """Helper to run main with patched sys.argv and mocked functions."""
        
        # Setup return values for mocked functions
        mock_find_files.return_value = [os.path.join(self.folder_path, "file1.csv")]
        mock_transactions_df = pd.DataFrame([{'amount': 100}]) # Mock DataFrame
        mock_load_combine.return_value = mock_transactions_df
        mock_get_analysis.return_value = "This is your financial analysis."

        original_argv = sys.argv
        sys.argv = args_list
        try:
            review_budget_main() # Call the aliased main from review_budget
        except SystemExit: # Catch sys.exit from argparse
            pass
        finally:
            sys.argv = original_argv


    @patch('review_budget.find_transaction_files')
    @patch('review_budget.load_and_combine_transactions')
    @patch('review_budget.get_financial_analysis')
    @patch('builtins.print')
    def test_main_success_flow(self, mock_print, mock_get_analysis, mock_load_combine, mock_find_files):
        """Test the main script flow for a successful case."""
        args = ["review_budget.py", self.folder_path, str(self.budget), self.api_key]
        self.run_main_with_mocks(args, mock_print, mock_get_analysis, mock_load_combine, mock_find_files)

        mock_find_files.assert_called_once_with(self.folder_path)
        found_files = mock_find_files.return_value
        mock_load_combine.assert_called_once_with(found_files)
        loaded_df = mock_load_combine.return_value
        mock_get_analysis.assert_called_once_with(loaded_df, self.budget, self.api_key)
        # Check if the analysis result was printed
        self.assertTrue(any(mock_get_analysis.return_value in str(c[0]) for c in mock_print.call_args_list))

    @patch('review_budget.find_transaction_files', return_value=[]) # No files found
    @patch('review_budget.load_and_combine_transactions') # Should not be called if no files
    @patch('review_budget.get_financial_analysis') # Should not be called
    @patch('builtins.print')
    def test_main_no_transaction_files_found(self, mock_print, mock_get_analysis, mock_load_combine, mock_find_files_empty):
        """Test main flow when no transaction files are found."""
        args = ["review_budget.py", self.folder_path, str(self.budget), self.api_key]
        self.run_main_with_mocks(args, mock_print, mock_get_analysis, mock_load_combine, mock_find_files_empty)
        
        mock_find_files_empty.assert_called_once_with(self.folder_path)
        mock_load_combine.assert_not_called()
        mock_get_analysis.assert_not_called()
        # Check for a message indicating no files were found / no analysis done
        self.assertTrue(any("No transaction files found" in str(c[0]) or "No data for analysis" in str(c[0]) for c in mock_print.call_args_list))


    @patch('review_budget.find_transaction_files') # Other mocks not strictly needed as argparse exits
    @patch('builtins.print')
    @patch('sys.exit')
    def test_main_missing_arguments(self, mock_sys_exit, mock_print, mock_find_files_unused):
        """Test main with missing required arguments."""
        args = ["review_budget.py", self.folder_path] # Missing budget and api_key
        self.run_main_with_mocks(args, mock_print, MagicMock(), MagicMock(), mock_find_files_unused)
        
        self.assertTrue(mock_print.called or mock_sys_exit.called)
        # Example check for argparse error message (depends on Python version and argparse setup)
        # self.assertTrue(any("the following arguments are required" in str(c[0]).lower() for c in mock_print.call_args_list))


    @patch('review_budget.find_transaction_files')
    @patch('builtins.print')
    @patch('sys.exit')
    def test_main_invalid_budget_argument(self, mock_sys_exit, mock_print, mock_find_files_unused):
        """Test main with a non-numeric budget argument."""
        args = ["review_budget.py", self.folder_path, "not_a_number", self.api_key]
        self.run_main_with_mocks(args, mock_print, MagicMock(), MagicMock(), mock_find_files_unused)

        self.assertTrue(mock_print.called or mock_sys_exit.called)
        # Example check for argparse error:
        # self.assertTrue(any("invalid float value" in str(c[0]).lower() for c in mock_print.call_args_list))


if __name__ == '__main__':
    # Pre-patch modules if review_budget.py imports them at top level
    if 'openai' not in sys.modules: # If openai was not imported because it's not installed
        sys.modules['openai'] = MagicMock(OpenAI=OpenAI, APIError=APIError, 
                                          AuthenticationError=AuthenticationError, RateLimitError=RateLimitError)
    if 'pd' not in sys.modules:
         sys.modules['pandas'] = pd # Our mocked pd (MagicMock or MockDataFrame holder)
            
    unittest.main()
