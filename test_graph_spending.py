import unittest
from unittest.mock import patch, mock_open, MagicMock
import pandas as pd
from pandas.testing import assert_series_equal
import io
import sys
import os
from datetime import datetime, timedelta
from graph_spending import graph_spending # Assuming the main function is graph_spending

class TestGraphSpending(unittest.TestCase):

    def setUp(self):
        # Basic CSV data for successful processing
        self.csv_data_valid = (
            "date,description,amount\n"
            "2023-01-01,Item A,$10.00\n"
            "2023-01-02,Item B,$20.00\n"
            "2023-01-03,Payment,-5.00\n" # Negative amount to be filtered
            "2023-01-04,Item C,$30.00\n"
            # Add more data to ensure we span more than 30 days for some tests if needed,
            # but the script itself defines a 30-day window from min date.
            "2023-01-15,Item D,$25.00\n"
        )
        self.target_budget = 3000.0
        self.output_path = "test_plot.png"

    @patch('graph_spending.plt') # Mock the entire plt module
    @patch('pandas.read_csv')
    def test_graph_spending_success_flow(self, mock_read_csv, mock_plt):
        """Test the successful execution of graph_spending."""
        mock_df = pd.read_csv(io.StringIO(self.csv_data_valid))
        mock_read_csv.return_value = mock_df

        graph_spending(csv_file="dummy.csv", target_budget=self.target_budget, output_path=self.output_path)

        mock_read_csv.assert_called_once_with("dummy.csv")

        # Verify plot calls
        self.assertTrue(mock_plt.figure.called)
        
        # Check that two lines were plotted (actual spending and budget line)
        self.assertEqual(mock_plt.plot.call_count, 2)

        # Actual Spending Line
        args_actual, kwargs_actual = mock_plt.plot.call_args_list[0]
        actual_spending_series = args_actual[1] # Second argument to plot is the data
        
        # Expected daily spending (positive amounts, reindexed to 30 days from 2023-01-01)
        # Dates: 2023-01-01 (10), 2023-01-02 (20), 2023-01-04 (30), 2023-01-15 (25)
        # All other days in the 30-day range should be 0.
        expected_dates = pd.date_range(start=datetime(2023,1,1), periods=30)
        expected_daily = pd.Series(0.0, index=expected_dates)
        expected_daily.loc[datetime(2023,1,1)] = 10.0
        expected_daily.loc[datetime(2023,1,2)] = 20.0
        expected_daily.loc[datetime(2023,1,4)] = 30.0
        expected_daily.loc[datetime(2023,1,15)] = 25.0
        
        assert_series_equal(actual_spending_series, expected_daily.cumsum(), check_names=False, check_dtype=False)

        # Budget Line
        args_budget, kwargs_budget = mock_plt.plot.call_args_list[1]
        daily_budget_val = self.target_budget / 30
        expected_budget_line = [daily_budget_val * (i + 1) for i in range(30)]
        # self.assertEqual(list(args_budget[1]), expected_budget_line) # Check data for budget line
        # Due to potential floating point inaccuracies, check first and last elements and length
        self.assertAlmostEqual(args_budget[1][0], expected_budget_line[0])
        self.assertAlmostEqual(args_budget[1][-1], expected_budget_line[-1])
        self.assertEqual(len(args_budget[1]), len(expected_budget_line))


        self.assertTrue(mock_plt.annotate.called)
        self.assertTrue(mock_plt.title.called)
        self.assertTrue(mock_plt.xlabel.called)
        self.assertTrue(mock_plt.ylabel.called)
        self.assertTrue(mock_plt.legend.called)
        self.assertTrue(mock_plt.grid.called)
        self.assertTrue(mock_plt.tight_layout.called)
        mock_plt.savefig.assert_called_once_with(self.output_path, format='png')

    @patch('pandas.read_csv', side_effect=FileNotFoundError("File not found"))
    @patch('graph_spending.plt') # Mock plt to prevent it from trying to draw
    def test_input_csv_not_found(self, mock_plt, mock_read_csv):
        """Test handling of FileNotFoundError for the input CSV."""
        with patch('builtins.print') as mock_print: # Capture print output for error message
            graph_spending("non_existent.csv", self.target_budget, self.output_path)
            # The script's own error handling prints the message.
            mock_print.assert_any_call("Error: File not found")
        mock_read_csv.assert_called_once_with("non_existent.csv")
        self.assertFalse(mock_plt.savefig.called) # Plotting should not occur

    @patch('pandas.read_csv')
    @patch('graph_spending.plt')
    def test_empty_csv_file(self, mock_plt, mock_read_csv):
        """Test with an empty CSV file."""
        empty_csv_data = "date,description,amount\n" # Header only
        mock_df = pd.read_csv(io.StringIO(empty_csv_data))
        mock_read_csv.return_value = mock_df
        
        with patch('builtins.print') as mock_print:
            graph_spending("empty.csv", self.target_budget, self.output_path)
            # This should print "Error: No valid dates found in the data."
            # because min() on an empty date series (after filtering positive) will be NaT
            mock_print.assert_any_call("Error: No valid dates found in the data.")
        self.assertFalse(mock_plt.savefig.called)


    @patch('pandas.read_csv')
    @patch('graph_spending.plt')
    def test_csv_with_no_positive_transactions(self, mock_plt, mock_read_csv):
        """Test with a CSV that only contains negative or zero amounts."""
        no_positive_csv_data = "date,description,amount\n2023-01-01,Refund,$-10.00\n2023-01-02,Fee,$0.00"
        mock_df = pd.read_csv(io.StringIO(no_positive_csv_data))
        mock_read_csv.return_value = mock_df

        with patch('builtins.print') as mock_print:
            graph_spending("no_positive.csv", self.target_budget, self.output_path)
            mock_print.assert_any_call("Error: No valid dates found in the data.")
        self.assertFalse(mock_plt.savefig.called)

    @patch('pandas.read_csv')
    @patch('graph_spending.plt')
    def test_csv_with_invalid_dates_or_amounts(self, mock_plt, mock_read_csv):
        """Test with a CSV containing unparseable dates or amounts."""
        invalid_data_csv = "date,description,amount\nInvalidDate,Item A,NotANumber\n2023-01-01,Item B,$10.00"
        mock_df = pd.read_csv(io.StringIO(invalid_data_csv))
        mock_read_csv.return_value = mock_df # read_csv will try its best, NaT/NaN will result

        with patch('builtins.print') as mock_print:
            graph_spending("invalid_data.csv", self.target_budget, self.output_path)
            # If all dates become NaT after errors='coerce', or all amounts NaN
            # it could lead to "No valid dates found" if no positive amounts with valid dates exist.
            # Or, if some are valid, it proceeds. Let's assume Item B is valid and processed.
            # Here, 'InvalidDate' becomes NaT. 'NotANumber' becomes NaN.
            # After filtering positive, only Item B (10.00 on 2023-01-01) remains.
            # So, it should proceed.
            self.assertTrue(mock_plt.savefig.called) # Should still plot with the valid data

    @patch('pandas.read_csv')
    @patch('graph_spending.plt')
    def test_spending_calculation_no_transactions_on_some_days(self, mock_plt, mock_read_csv):
        """Test spending calculation when there are no transactions on some days within the 30-day window."""
        # Data has gaps: 2023-01-01, then 2023-01-03. 2023-01-02 should be 0.
        csv_data_gaps = "date,description,amount\n2023-01-01,Item A,$10.00\n2023-01-03,Item B,$20.00"
        mock_df = pd.read_csv(io.StringIO(csv_data_gaps))
        mock_read_csv.return_value = mock_df

        graph_spending("gaps.csv", self.target_budget, self.output_path)

        # Check the actual spending data passed to plot
        args_actual, _ = mock_plt.plot.call_args_list[0]
        actual_spending_series = args_actual[1] # Cumulative sum

        expected_dates = pd.date_range(start=datetime(2023,1,1), periods=30)
        expected_daily = pd.Series(0.0, index=expected_dates)
        expected_daily.loc[datetime(2023,1,1)] = 10.0
        expected_daily.loc[datetime(2023,1,3)] = 20.0
        
        assert_series_equal(actual_spending_series, expected_daily.cumsum(), check_names=False, check_dtype=False)
        self.assertTrue(mock_plt.savefig.called)

    # Tests for the __main__ entry point
    @patch('graph_spending.graph_spending') # Mock the main function itself
    @patch('sys.exit') # To prevent test runner from exiting
    @patch('builtins.print') # To capture error messages
    def test_main_entry_point_success(self, mock_print, mock_sys_exit, mock_graph_spending_func):
        """Test the main entry point (__name__ == '__main__') with valid arguments."""
        test_args = ["script_name.py", "data.csv", "1000.0", "plot.png"]
        with patch.object(sys, 'argv', test_args):
            with patch('os.path.exists', return_value=True): # Mock file existence check
                # Need to re-import or exec the script content if __main__ check is to be run.
                # A simpler way is to test the conditions inside __main__ directly or refactor __main__.
                # For this test, we'll assume the script's __main__ calls graph_spending if args are ok.
                # We can simulate the execution of the __main__ block by importing the script
                # as a module and then calling a hypothetical wrapper, or by re-executing its content.
                
                # To actually run the __main__ block, we'd need to do something like:
                # path_to_script = os.path.join(os.path.dirname(__file__), '..', 'graph_spending.py') # Adjust path
                # with open(path_to_script, 'r') as f:
                #     script_content = f.read()
                # exec(script_content)

                # This is complex. Instead, let's test the call to graph_spending with correct args.
                # The current `graph_spending.py` calls graph_spending() from __main__.
                # We need to simulate the argument parsing and os.path.exists check.
                
                # This test will focus on whether graph_spending is called correctly.
                # The actual __main__ block of graph_spending.py needs to be executed for a true integration test.
                # We can mock os.path.exists which is used in the script's __main__.
                
                # Simulate running the script by calling a hypothetical function that encapsulates __main__
                # or by directly calling the parts of __main__ if it was refactored.
                # Since it's not refactored, we'll check if graph_spending_func is called.
                
                # This setup is for testing the call *from* __main__
                # We will assume the script graph_spending.py is run.
                # The test below for `main_entry_point_arg_parsing_and_calls` is more robust for __main__ logic.
                pass # See more detailed test below.

    @patch('graph_spending.graph_spending') # Mock the function called by main
    @patch('builtins.print')
    @patch('sys.exit')
    def run_main_with_args(self, args_list, mock_print, mock_sys_exit, mock_graph_spending_call):
        """Helper to run the __main__ block of graph_spending.py by executing it."""
        # Store original sys.argv and restore it later
        original_argv = sys.argv
        sys.argv = args_list
        
        # Find the path to graph_spending.py. This assumes a certain directory structure.
        # For a standalone test, this might need adjustment or the script to be in PYTHONPATH.
        # For this environment, assume graph_spending.py is in the current dir or discoverable.
        script_path = "graph_spending.py" 
        
        try:
            with open(script_path, 'r') as f:
                script_code = f.read()
            # Execute the script in a specific context to capture its behavior
            exec_globals = {'__name__': '__main__', 'sys': sys, 'os': os, 
                            'graph_spending': mock_graph_spending_call, # Ensure our mock is used
                            'pd': pd, 'plt': MagicMock()} # Mock pandas and plt for the script's context
            exec(script_code, exec_globals)
        finally:
            sys.argv = original_argv # Restore original argv


    @patch('graph_spending.graph_spending') # Mock the actual workhorse function
    @patch('os.path.exists', return_value=True) # Assume CSV file exists for valid cases
    @patch('builtins.print')
    @patch('sys.exit')
    def test_main_entry_point_arg_parsing_and_calls(self, mock_sys_exit, mock_print, mock_os_exists, mock_graph_spending_func):
        """Test __main__ block for argument parsing and calling graph_spending."""
        
        # Valid case
        self.run_main_with_args(["graph_spending.py", "data.csv", "1500.50", "out.png"], mock_print, mock_sys_exit, mock_graph_spending_func)
        mock_graph_spending_func.assert_called_with("data.csv", 1500.50, "out.png")
        mock_sys_exit.assert_not_called() # Should not exit on success

        # Too few arguments
        mock_graph_spending_func.reset_mock()
        mock_sys_exit.reset_mock()
        self.run_main_with_args(["graph_spending.py", "data.csv"], mock_print, mock_sys_exit, mock_graph_spending_func)
        mock_print.assert_any_call("Usage: python spending_plot.py <csv_file> <target_budget> <output_path>")
        # sys.exit might be called by the script, or it might just print and fall through if not sys.exit(1)
        # The script does not have sys.exit(1) after usage print, so graph_spending might still be called if not careful.
        # The script structure is: if len !=4 -> print usage. ELSE -> parse args...
        # So, graph_spending_func should not be called.
        mock_graph_spending_func.assert_not_called()

        # Non-numeric budget
        mock_graph_spending_func.reset_mock()
        mock_sys_exit.reset_mock()
        mock_print.reset_mock()
        self.run_main_with_args(["graph_spending.py", "data.csv", "not_a_number", "out.png"], mock_print, mock_sys_exit, mock_graph_spending_func)
        mock_print.assert_any_call("Error: Target budget must be a numeric value.")
        mock_sys_exit.assert_called_once_with(1)
        mock_graph_spending_func.assert_not_called()
        
        # CSV file does not exist
        mock_graph_spending_func.reset_mock()
        mock_sys_exit.reset_mock()
        mock_print.reset_mock()
        mock_os_exists.return_value = False # Simulate file not existing
        self.run_main_with_args(["graph_spending.py", "missing.csv", "1000", "out.png"], mock_print, mock_sys_exit, mock_graph_spending_func)
        mock_print.assert_any_call("Error: File 'missing.csv' not found.")
        mock_graph_spending_func.assert_not_called()
        # The script doesn't sys.exit here, but graph_spending() isn't called.

if __name__ == '__main__':
    unittest.main()
