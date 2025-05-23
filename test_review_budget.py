import unittest
from unittest.mock import patch, mock_open, MagicMock
import os
import sys
import datetime
import pandas as pd
from pandas.testing import assert_frame_equal
import shutil

# Add the directory containing review_budget to sys.path
# This is to ensure that the tests can import review_budget
# This might be needed depending on how the test runner is invoked
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

try:
    import review_budget
except ImportError:
    print("Failed to import review_budget. Make sure it's in the Python path.")
    sys.exit(1)


class TestGetLastNMonthsFiles(unittest.TestCase):
    @patch('review_budget.datetime.date')
    def test_get_last_n_months_files_logic(self, mock_date):
        # Test cases: (today_date, num_months, expected_filenames)
        test_scenarios = [
            (datetime.date(2024, 3, 15), 1, ["February 2024 - transactions.csv"]),
            (datetime.date(2024, 3, 15), 3, ["February 2024 - transactions.csv", "January 2024 - transactions.csv", "December 2023 - transactions.csv"]),
            (datetime.date(2024, 1, 5), 3, ["December 2023 - transactions.csv", "November 2023 - transactions.csv", "October 2023 - transactions.csv"]),
            (datetime.date(2023, 12, 31), 12, [
                "November 2023 - transactions.csv", "October 2023 - transactions.csv", "September 2023 - transactions.csv",
                "August 2023 - transactions.csv", "July 2023 - transactions.csv", "June 2023 - transactions.csv",
                "May 2023 - transactions.csv", "April 2023 - transactions.csv", "March 2023 - transactions.csv",
                "February 2023 - transactions.csv", "January 2023 - transactions.csv", "December 2022 - transactions.csv"
            ]),
            (datetime.date(2024, 1, 20), 13, [
                "December 2023 - transactions.csv", "November 2023 - transactions.csv", "October 2023 - transactions.csv",
                "September 2023 - transactions.csv", "August 2023 - transactions.csv", "July 2023 - transactions.csv",
                "June 2023 - transactions.csv", "May 2023 - transactions.csv", "April 2023 - transactions.csv",
                "March 2023 - transactions.csv", "February 2023 - transactions.csv", "January 2023 - transactions.csv",
                "December 2022 - transactions.csv"
            ]),
        ]

        test_folder = "test_transactions_folder"
        if not os.path.exists(test_folder):
            os.makedirs(test_folder)

        for today_date, num_months, expected_filenames in test_scenarios:
            mock_date.today.return_value = today_date
            
            expected_paths = [os.path.join(test_folder, f) for f in expected_filenames]
            
            with self.subTest(today=today_date, num_months=num_months):
                actual_paths = review_budget.get_last_n_months_files(test_folder, num_months)
                self.assertEqual(len(actual_paths), len(expected_paths))
                self.assertListEqual(actual_paths, expected_paths)
        
        if os.path.exists(test_folder):
            shutil.rmtree(test_folder)


class TestConcatenateTransactions(unittest.TestCase):
    def setUp(self):
        self.test_dir = "temp_test_data"
        os.makedirs(self.test_dir, exist_ok=True)
        
        # Create dummy CSV files
        self.df1_data = {'Date': ['2023-01-01'], 'Amount': [100]}
        self.df2_data = {'Date': ['2023-02-01'], 'Amount': [200]}
        self.df_empty_data = {} # For empty file
        self.df_combined_data = {'Date': ['2023-01-01', '2023-02-01'], 'Amount': [100, 200]}

        pd.DataFrame(self.df1_data).to_csv(os.path.join(self.test_dir, "Month1_2023_-_transactions.csv"), index=False)
        pd.DataFrame(self.df2_data).to_csv(os.path.join(self.test_dir, "Month2_2023_-_transactions.csv"), index=False)
        # For empty file test
        with open(os.path.join(self.test_dir, "Month_Empty_-_transactions.csv"), 'w') as f:
            pass 
        # For invalid CSV test
        with open(os.path.join(self.test_dir, "Month_Invalid_-_transactions.csv"), 'w') as f:
            f.write("this,is,not,a,valid,csv\nbut,has,two,lines")

        self.mock_files = [
            os.path.join(self.test_dir, "Month1_2023_-_transactions.csv"),
            os.path.join(self.test_dir, "Month2_2023_-_transactions.csv"),
            os.path.join(self.test_dir, "NonExistent_Month_-_transactions.csv"),
            os.path.join(self.test_dir, "Month_Empty_-_transactions.csv"),
            os.path.join(self.test_dir, "Month_Invalid_-_transactions.csv"),
        ]

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    @patch('review_budget.get_last_n_months_files')
    @patch('review_budget.print') # To capture print statements
    def test_all_files_exist_and_valid(self, mock_print, mock_get_files):
        mock_get_files.return_value = [self.mock_files[0], self.mock_files[1]]
        
        output_file, combined_df = review_budget.concatenate_transactions(self.test_dir, 2)
        
        expected_df = pd.DataFrame(self.df_combined_data)
        assert_frame_equal(combined_df.reset_index(drop=True), expected_df.reset_index(drop=True))
        self.assertEqual(output_file, os.path.join(self.test_dir, "combined_transactions.csv"))
        self.assertTrue(os.path.exists(output_file))
        
        # Check if the output CSV content is correct
        saved_df = pd.read_csv(output_file)
        assert_frame_equal(saved_df, expected_df)
        mock_print.assert_any_call("Found and successfully read 2 transaction file(s).")


    @patch('review_budget.get_last_n_months_files')
    @patch('review_budget.print')
    def test_some_files_missing(self, mock_print, mock_get_files):
        # Only first file exists, second is NonExistent
        mock_get_files.return_value = [self.mock_files[0], self.mock_files[2]] 
        
        output_file, combined_df = review_budget.concatenate_transactions(self.test_dir, 2)
        
        expected_df = pd.DataFrame(self.df1_data)
        assert_frame_equal(combined_df.reset_index(drop=True), expected_df.reset_index(drop=True))
        self.assertTrue(os.path.exists(output_file))
        mock_print.assert_any_call(f"Info: Missing file {self.mock_files[2]}, skipping.")
        mock_print.assert_any_call("Found and successfully read 1 transaction file(s).")

    @patch('review_budget.get_last_n_months_files')
    @patch('review_budget.sys.exit')
    @patch('review_budget.print')
    def test_all_files_missing(self, mock_print, mock_sys_exit, mock_get_files):
        mock_get_files.return_value = [self.mock_files[2]] # NonExistent file
        
        review_budget.concatenate_transactions(self.test_dir, 1)
        
        mock_print.assert_any_call(f"Info: Missing file {self.mock_files[2]}, skipping.")
        mock_print.assert_any_call("Error: No transaction files found for the specified period.")
        mock_sys_exit.assert_called_once_with(1)

    @patch('review_budget.get_last_n_months_files')
    @patch('review_budget.print')
    def test_one_file_empty_and_one_invalid(self, mock_print, mock_get_files):
        # Files: valid, empty, invalid
        mock_get_files.return_value = [self.mock_files[0], self.mock_files[3], self.mock_files[4]]
        
        output_file, combined_df = review_budget.concatenate_transactions(self.test_dir, 3)
        
        expected_df = pd.DataFrame(self.df1_data) # Only the first file's data
        assert_frame_equal(combined_df.reset_index(drop=True), expected_df.reset_index(drop=True))
        self.assertTrue(os.path.exists(output_file))
        
        # Check for print calls related to empty and invalid files
        # For empty file, pandas might read it as an empty DataFrame without error, or with a specific error.
        # Depending on pandas version, an empty file might raise an EmptyDataError or return an empty DataFrame.
        # If it returns an empty DataFrame, it will be part of `dfs` and `concat` handles it.
        # The current code in `review_budget.py` has a try-except for `pd.read_csv`.
        # An empty file might result in an error like "No columns to parse from file"
        mock_print.assert_any_call(f"Error reading file {self.mock_files[3]}: EmptyDataError('No columns to parse from file')" if pd.__version__ < "2.0.0" else f"Error reading file {self.mock_files[3]}: EmptyDataError('No columns to parse from file: {self.mock_files[3]}')")
        mock_print.assert_any_call(f"Error reading file {self.mock_files[4]}: ParserError('Error tokenizing data. C error: Expected 1 fields in line 2, saw 2')")
        mock_print.assert_any_call("Found and successfully read 1 transaction file(s).")


class TestAnalyzeTransactionsPrompt(unittest.TestCase):
    @patch('review_budget.requests.post')
    @patch('review_budget.pd.read_csv') # Mock reading the csv to avoid file IO
    def test_prompt_construction(self, mock_read_csv, mock_post):
        # Mock pd.read_csv to return a dummy DataFrame
        mock_df = pd.DataFrame({'col1': [1], 'col2': [2]})
        mock_read_csv.return_value = mock_df
        
        # Mock the response from requests.post
        mock_response = MagicMock()
        mock_response.json.return_value = {"choices": [{"message": {"content": "Analysis complete."}}]}
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        api_key = "test_api_key"
        budget = 1000
        transactions_csv_path = "dummy_transactions.csv" # Path doesn't matter due to mocking read_csv

        scenarios = [
            (1, "last month", "over these 1 months"),
            (3, "last 3 months", "over these 3 months")
        ]

        for num_months, expected_month_string, expected_trend_period_string in scenarios:
            with self.subTest(num_months=num_months):
                review_budget.analyze_transactions(api_key, budget, transactions_csv_path, num_months)
                
                # Check that requests.post was called
                mock_post.assert_called()
                
                # Get the arguments passed to requests.post
                args, kwargs = mock_post.call_args
                called_data = kwargs['json'] # The 'data' payload is passed as 'json' in requests.post
                
                prompt_text = called_data['messages'][1]['content'] # User message content
                
                self.assertIn(f"Review my transactions for the {expected_month_string}", prompt_text)
                self.assertIn(f"against my budget of ${budget}", prompt_text)
                self.assertIn("Summarize where most of my spending went.", prompt_text)
                self.assertIn("Identify if my overall spending is increasing or decreasing across this period.", prompt_text)
                self.assertIn(f"Note any other significant trends, patterns, or anomalies you observe in the spending data {expected_trend_period_string}.", prompt_text)
                self.assertIn(mock_df.to_string(index=False), prompt_text) # Check if transaction data is in prompt
                self.assertEqual(called_data['max_tokens'], 500)
                self.assertEqual(called_data['model'], "gpt-4")

if __name__ == '__main__':
    unittest.main(argv=['first-arg-is-ignored'], exit=False)

# Note: The test for empty/invalid file in TestConcatenateTransactions might need adjustment
# based on the exact pandas errors thrown for empty or malformed CSVs, which can vary slightly
# between pandas versions. The provided error messages in the assert_any_call are common ones.
# Added a check for pandas version for EmptyDataError message.

# The test for TestGetLastNMonthsFiles creates and deletes a dummy folder "test_transactions_folder"
# to ensure os.path.join works as expected and the test is self-contained.

# For TestAnalyzeTransactionsPrompt, pd.read_csv is mocked to avoid needing an actual CSV file
# for testing the prompt construction logic.
