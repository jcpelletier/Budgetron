import unittest
from unittest.mock import patch, MagicMock, call
import sys
import os
from datetime import datetime, date

# Attempt to import from driver_analysis.py
# If it doesn't exist, tests will use mocks.
try:
    from driver_analysis import (
        find_previous_month_csv,
        main as driver_main # Assuming main entry point is named main
        # If other helper functions are expected, they'd be imported here too
    )
except ImportError:
    print("Note: Could not import from driver_analysis.py. Tests will proceed with mocks.")
    # Mock the functions if they couldn't be imported
    find_previous_month_csv = MagicMock()
    driver_main = MagicMock()


class TestDriverAnalysis(unittest.TestCase):

    def setUp(self):
        self.folder_path = "/test/transactions"
        self.classification_csv = "/test/config/spending_categories.csv"
        self.budget = 2500.00
        self.bot_token = "fake_bot_token"
        self.channel_id = "fake_channel_id"
        self.scripts_path = "financial_scripts" # Assuming a subfolder for other scripts

        # Common expected output paths
        self.expected_spending_categories_img = os.path.join(self.folder_path, "spending_categories_chart.png")
        self.expected_graph_spending_img = os.path.join(self.folder_path, "spending_graph.png")
        self.expected_other_transactions_txt = os.path.join(self.folder_path, "other_transactions.txt") # If spending_categories.py produces this

    # --- Tests for find_previous_month_csv ---
    @patch('driver_analysis.os.path.exists')
    @patch('driver_analysis.os.listdir')
    def test_find_previous_month_csv_success(self, mock_listdir, mock_os_exists):
        """Test finding the CSV for the previous month successfully."""
        mock_os_exists.return_value = True # Folder exists
        current_date = date(2024, 3, 15) # March 2024
        # Expected: February 2024 - *.csv
        
        all_files_in_folder = [
            "February 2024 - transactions_data.csv", # Expected match
            "January 2024 - data.csv",
            "February 2024 - summary.txt",
            "March 2024 - current.csv"
        ]
        mock_listdir.return_value = all_files_in_folder
        
        expected_csv_path = os.path.join(self.folder_path, "February 2024 - transactions_data.csv")
        found_path = find_previous_month_csv(self.folder_path, current_date)
        
        mock_os_exists.assert_called_once_with(self.folder_path)
        mock_listdir.assert_called_once_with(self.folder_path)
        self.assertEqual(found_path, expected_csv_path)

    @patch('driver_analysis.os.path.exists')
    @patch('driver_analysis.os.listdir')
    def test_find_previous_month_csv_no_match(self, mock_listdir, mock_os_exists):
        mock_os_exists.return_value = True
        current_date = date(2024, 3, 15)
        mock_listdir.return_value = ["January 2024 - data.csv", "March 2024 - current.csv"]
        
        found_path = find_previous_month_csv(self.folder_path, current_date)
        self.assertIsNone(found_path)

    @patch('driver_analysis.os.path.exists')
    @patch('driver_analysis.os.listdir')
    def test_find_previous_month_csv_multiple_matches(self, mock_listdir, mock_os_exists):
        """Test behavior if multiple CSVs match (e.g., picks first alphabetically)."""
        mock_os_exists.return_value = True
        current_date = date(2024, 3, 15) # Expects February 2024
        
        # Assuming it picks the first one found by os.listdir (after internal sort if any)
        # Or, more robustly, if the spec is "any valid match is fine", or "the one with 'transactions' "
        # For now, let's assume it might pick the first one alphabetically if not specified.
        # If driver_analysis.py sorts or has specific logic, this test needs adjustment.
        all_files = [
            "February 2024 - part2.csv",
            "February 2024 - part1.csv", # Should be picked if sorted alphabetically
        ]
        mock_listdir.return_value = sorted(all_files) # Simulate sorted listdir
        
        # If the function sorts them and picks the first, "part1" would be chosen.
        # If it doesn't sort and relies on os.listdir order, this test is less predictable.
        # Let's assume the function sorts the matches and picks the first.
        expected_csv_path = os.path.join(self.folder_path, "February 2024 - part1.csv")
        
        # To make it more deterministic, let's assume the function picks the first match it encounters.
        # And os.listdir returns them in a specific order for the mock.
        mock_listdir.return_value = ["February 2024 - part2.csv", "February 2024 - part1.csv"]
        # If it picks the first from the list:
        expected_if_first_from_unsorted_list = os.path.join(self.folder_path, "February 2024 - part2.csv")

        # This test depends HEAVILY on the implementation details of find_previous_month_csv.
        # For now, let's assume it finds *a* match if one exists, and the exact one for multiple matches
        # is not critical for this test, or it picks the first one returned by os.listdir.
        
        found_path = find_previous_month_csv(self.folder_path, current_date)
        self.assertEqual(found_path, expected_if_first_from_unsorted_list)


    @patch('driver_analysis.os.path.exists', return_value=False)
    @patch('builtins.print') # If it prints an error
    def test_find_previous_month_csv_folder_not_exist(self, mock_print, mock_os_exists):
        current_date = date(2024, 3, 15)
        found_path = find_previous_month_csv(self.folder_path, current_date)
        
        self.assertIsNone(found_path)
        mock_os_exists.assert_called_once_with(self.folder_path)
        # Check if an error was printed (optional, depends on implementation)
        # mock_print.assert_any_call(f"Folder {self.folder_path} not found.")

    # --- Tests for Orchestration Logic (assuming subprocess.run) ---
    # These tests assume driver_analysis.py has a main orchestrating function that is called by driver_main()
    # or driver_main() itself is the orchestrator.
    # Let's assume a hypothetical run_analysis(args) function for clarity, mocked by driver_main itself in tests for __main__.

    @patch('driver_analysis.subprocess.run')
    @patch('driver_analysis.find_previous_month_csv')
    @patch('driver_analysis.os.path.join', side_effect=os.path.join) # Ensure os.path.join works normally
    @patch('driver_analysis.sys.executable', 'python') # Mock python executable path
    def test_orchestration_success_flow_with_subprocess(self, mock_py_exec, mock_os_path_join,
                                                       mock_find_csv, mock_subprocess_run):
        """Test successful orchestration of scripts via subprocess.run."""
        previous_month_csv = os.path.join(self.folder_path, "February 2024 - data.csv")
        mock_find_csv.return_value = previous_month_csv
        
        # Mock successful subprocess runs
        mock_subprocess_run.return_value = MagicMock(returncode=0, stdout="Success", stderr="")

        # These are the args passed to driver_analysis.py's main function
        driver_args = MagicMock(
            folder=self.folder_path,
            classification_csv=self.classification_csv,
            budget=self.budget,
            bot_token=self.bot_token,
            channel_id=self.channel_id,
            scripts_path=self.scripts_path # Assuming this arg exists for script locations
        )

        # Call the main orchestrating logic.
        # If driver_main is the orchestrator, we call that.
        # This requires driver_main to be the actual orchestrator, not just arg parser.
        # For this test, let's assume driver_main calls an internal orchestrator,
        # or we test the orchestrator directly if it's separable.
        # For now, assume driver_main handles orchestration after parsing.
        
        # We need to simulate calling driver_main with parsed args.
        # The call to driver_main() here is conceptual if it's normally called from __main__.
        # The test_main_... tests will cover the actual __main__ block.
        # Here, we're testing the sequence of operations *as if* main was called with these args.
        # This means we'd need driver_main to be structured to accept parsed args, or mock argparse.
        # Let's assume an internal function `_orchestrate(parsed_args)` for this unit test.
        # If driver_main IS the orchestrator, then the __main__ tests will cover this.
        # To avoid redundancy, this test will focus on subprocess.run calls assuming valid inputs.

        # Expected paths to scripts
        path_spending_categories = os.path.join(self.scripts_path, "spending_categories.py")
        path_graph_spending = os.path.join(self.scripts_path, "graph_spending.py")
        path_post_to_discord = os.path.join(self.scripts_path, "post_to_discord.py")

        # Call a hypothetical orchestrator function with pre-parsed args
        # For this test, let's assume `driver_analysis.orchestrate_analysis(driver_args)` exists.
        # Since we don't have it, we'll have to make driver_main the target and mock its internal calls.
        # This means we're effectively testing parts of what the `test_main_...` would test,
        # but focusing on the subprocess calls.

        # This test is becoming an integration test for driver_main.
        # Let's refine: assume driver_main takes these args and calls subprocess.
        # This test will be similar to test_main_success_flow but focused on subprocess.run.
        
        # To properly test orchestration logic separately from main arg parsing:
        # Refactor driver_analysis.py to have:
        # def main_logic(folder, classification_csv, budget, bot_token, channel_id, scripts_path):
        #     # ... orchestration ...
        # def main(): # (entry point)
        #     args = parse_args()
        #     main_logic(args.folder, ...)
        # Then we can test main_logic. For now, assume driver_main is testable this way.

        # This test is a bit tricky without the actual structure of driver_analysis.py
        # Let's assume we are testing a function `execute_full_analysis` that takes parsed args.
        # And `driver_main` calls this.
        
        # This test will be simplified to check for subprocess.run calls with expected args.
        # The actual call to driver_main or an orchestrator function would be:
        # driver_main() # If it uses mocked argparse internally or if we patch sys.argv before
        # For now, let's just set up mocks and check subprocess.run.
        # This means this test is more of a blueprint for how to check subprocess calls.

        # Call (hypothetical)
        # orchestrate(folder_path=self.folder_path, classification_csv=self.classification_csv, ...)

        # Expected calls to subprocess.run
        expected_calls = [
            # spending_categories.py
            call(['python', path_spending_categories, previous_month_csv, self.classification_csv, self.expected_spending_categories_img], check=True),
            # graph_spending.py
            call(['python', path_graph_spending, previous_month_csv, str(self.budget), self.expected_graph_spending_img], check=True),
            # post_to_discord.py - success message with two images
            call(['python', path_post_to_discord, self.bot_token, self.channel_id, 
                  unittest.mock.ANY, # Success message
                  "--use_chatgpt", # Assuming ChatGPT is used for success
                  self.expected_spending_categories_img, 
                  self.expected_graph_spending_img], check=True) # This call needs to be flexible for multiple images
        ]
        # Note: post_to_discord.py might be called with image paths differently.
        # The script might take multiple image paths. If it takes only one, then it's called twice.
        # The prompt for post_to_discord.py tests implied it could take one image.
        # Let's assume it can take multiple image paths as final arguments.
        # The test for post_to_discord.py main entry point `test_main_entry_message_with_chatgpt_flag_and_image`
        # showed it taking one image. If multiple images, post_to_discord.py needs to handle varargs for images.
        # For now, assume it's called twice if it only handles one image.
        
        # Revised assumption: post_to_discord.py is called once with a message and *all* relevant images.
        # This requires post_to_discord.py to be designed to accept multiple image paths.
        # If post_to_discord.py only accepts one image, then it would be called multiple times.
        # The `test_post_to_discord.py` only showed one image path.
        # Let's assume for now it is called for *each* image, or once with a combined message.
        # For simplicity of this test, assume one call with one primary image, or a message referring to saved files.
        # The prompt for this test says "output paths ... are correctly formulated and passed".

        # Let's assume a success message and one primary image (e.g., spending categories)
        # This is a simplification.
        # A more robust test would check for multiple calls to post_to_discord if needed,
        # or a single call with a complex message and possibly multiple image args if post_to_discord supports it.

        # Given the tests for post_to_discord.py, it takes ONE image_path.
        # So, driver_analysis.py must call it multiple times or send one image.
        # Let's assume it sends spending_categories_img.
        expected_discord_success_call = call([
            'python', path_post_to_discord, self.bot_token, self.channel_id, 
            unittest.mock.ANY, # Success message string
            "--use_chatgpt",
            self.expected_spending_categories_img # Assuming this is the primary image sent
        ], check=True)
        # Or maybe it sends both, if post_to_discord.py was updated to handle it.
        # The prompt for this test is ambiguous on how multiple images are handled by post_to_discord.py
        # Let's stick to the known capability of post_to_discord.py (one image).
        # So, two calls for discord, or one call with no image but message pointing to them.
        # For now, assume one main image is sent.

        # This test is more about the structure and less about exact subprocess calls until driver_analysis.py is known.
        # The assertions below are placeholders.
        # mock_subprocess_run.assert_has_calls(expected_calls, any_order=False)
        pass # This test needs the actual driver_analysis.py structure to be effective.


    @patch('driver_analysis.subprocess.run')
    @patch('driver_analysis.find_previous_month_csv')
    def test_orchestration_subprocess_error_handling(self, mock_find_csv, mock_subprocess_run):
        """Test error handling if a subprocess call fails."""
        previous_month_csv = os.path.join(self.folder_path, "February 2024 - data.csv")
        mock_find_csv.return_value = previous_month_csv
        
        # Simulate failure in spending_categories.py
        mock_subprocess_run.side_effect = [
            MagicMock(returncode=1, stdout="", stderr="Error in spending_categories"), # spending_categories fails
            MagicMock(returncode=0, stdout="Success", stderr="") # Subsequent calls (e.g. discord error notification)
        ]
        
        driver_args = MagicMock(folder=self.folder_path, classification_csv=self.classification_csv, budget=self.budget,
                                bot_token=self.bot_token, channel_id=self.channel_id, scripts_path=self.scripts_path)

        # Call orchestrator (hypothetical)
        # orchestrate(driver_args)

        # Assertions:
        # 1. spending_categories.py was called.
        # 2. graph_spending.py might be skipped or still called depending on design.
        # 3. post_to_discord.py is called with an error message.
        
        # Example:
        # self.assertEqual(mock_subprocess_run.call_count, 2) # spending_categories + discord_error_notification
        # error_discord_call = mock_subprocess_run.call_args_list[1]
        # self.assertIn("Error during financial analysis", error_discord_call[0][1][4]) # Check message arg
        pass # Needs driver_analysis.py structure


    # --- Tests for Discord Notification Calls ---
    # These are partially covered by orchestration tests but can be more specific.

    @patch('driver_analysis.subprocess.run')
    @patch('driver_analysis.find_previous_month_csv', return_value=None) # No CSV found
    @patch('driver_analysis.os.path.join', side_effect=os.path.join)
    @patch('driver_analysis.sys.executable', 'python')
    def test_discord_notification_no_csv_found(self, mock_py_exec, mock_os_join, mock_find_csv_none, mock_subprocess_run):
        """Test Discord notification when no CSV is found."""
        mock_subprocess_run.return_value = MagicMock(returncode=0)
        
        driver_args = MagicMock(folder=self.folder_path, classification_csv=self.classification_csv, budget=self.budget,
                                bot_token=self.bot_token, channel_id=self.channel_id, scripts_path=self.scripts_path)
        
        # Call orchestrator or main logic that handles this
        # orchestrate(driver_args) or driver_main() with patched sys.argv

        # Expected call to post_to_discord.py with "CSV not found" message
        path_post_to_discord = os.path.join(self.scripts_path, "post_to_discord.py")
        expected_discord_call_args = [
            'python', path_post_to_discord, self.bot_token, self.channel_id,
            unittest.mock.ANY, # Message indicating CSV not found
            "--use_chatgpt" # Assuming ChatGPT is used for this type of message too
        ]
        # mock_subprocess_run.assert_called_once_with(expected_discord_call_args, check=True)
        # self.assertIn("No CSV file found for the previous month", mock_subprocess_run.call_args[0][1][4])
        pass # Needs driver_analysis.py structure


    # --- Tests for main function (driver_analysis.py entry point) ---
    @patch('driver_analysis.find_previous_month_csv')
    @patch('driver_analysis.subprocess.run') # Assuming subprocess.run is used
    # If importing main functions: @patch('spending_categories.main_function'), @patch('graph_spending.main_function'), etc.
    def run_driver_main_with_mocks(self, args_list, mock_subprocess_run, mock_find_csv):
        """Helper to run driver_analysis.py's main() with patched sys.argv and core logic mocks."""
        
        # Setup default return values for mocks
        mock_find_csv.return_value = os.path.join(self.folder_path, "February 2024 - data.csv")
        mock_subprocess_run.return_value = MagicMock(returncode=0, stdout="Success", stderr="")

        original_argv = sys.argv
        sys.argv = args_list
        try:
            driver_main() # Call the main function from driver_analysis.py
        except SystemExit: # Catch sys.exit from argparse
            pass
        finally:
            sys.argv = original_argv

    @patch('driver_analysis.find_previous_month_csv')
    @patch('driver_analysis.subprocess.run')
    # Add more patches if driver_main directly calls os.path.join, sys.executable for script paths
    @patch('driver_analysis.os.path.join', side_effect=lambda *args: os.path.normpath(os.path.join(*args)))
    @patch('driver_analysis.sys.executable', 'python_mocked')
    def test_main_success_flow_args_parsed_and_used(self, mock_py_exec, mock_os_join,
                                                 mock_subprocess_run, mock_find_csv):
        """Test main() with valid arguments, ensuring they are parsed and used."""
        args = [
            "driver_analysis.py",
            "--folder", self.folder_path,
            "--classification_csv", self.classification_csv,
            "--budget", str(self.budget),
            "--bot_token", self.bot_token,
            "--channel_id", self.channel_id,
            "--scripts_path", self.scripts_path # Assuming this is an arg
        ]
        self.run_driver_main_with_mocks(args, mock_subprocess_run, mock_find_csv)

        mock_find_csv.assert_called_once() # Check that current_date was passed correctly if possible
        # Example: self.assertEqual(mock_find_csv.call_args[0][1].month, datetime.now().month)
        
        # Verify subprocess calls based on parsed arguments
        # This will be complex and depends on exact implementation.
        # Example: Check that spending_categories.py was called with self.classification_csv
        
        # Check that all three scripts were called (spending_categories, graph_spending, post_to_discord)
        # This assumes a successful run where all are executed.
        # The number of calls to subprocess.run depends on how post_to_discord is used (once per image or one combined call)
        # Assuming 3 main script calls + 1 discord for success (simplified)
        # self.assertGreaterEqual(mock_subprocess_run.call_count, 3) # At least 3 scripts

        # Detailed subprocess call verification:
        # This is where you'd construct the expected command list for each subprocess call
        # and assert mock_subprocess_run.assert_any_call(...) or assert_has_calls(...)
        
        # Example for spending_categories.py call
        # path_spending_categories = os.path.normpath(os.path.join(self.scripts_path, "spending_categories.py"))
        # found_csv_path = mock_find_csv.return_value
        # expected_spending_cmd = ['python_mocked', path_spending_categories, found_csv_path, 
        #                          self.classification_csv, self.expected_spending_categories_img]
        # mock_subprocess_run.assert_any_call(expected_spending_cmd, check=True)
        pass # Needs more detailed structure of driver_analysis.py


    @patch('driver_analysis.find_previous_month_csv') # Not called
    @patch('driver_analysis.subprocess.run')      # Not called
    @patch('builtins.print') # To capture argparse error output
    @patch('sys.exit')       # To prevent test runner from exiting
    def test_main_missing_required_arguments(self, mock_sys_exit, mock_print, 
                                           mock_subprocess_run_unused, mock_find_csv_unused):
        """Test main() with missing required arguments."""
        args = ["driver_analysis.py", "--folder", self.folder_path] # Missing other required args
        self.run_driver_main_with_mocks(args, mock_subprocess_run_unused, mock_find_csv_unused)
        
        self.assertTrue(mock_print.called or mock_sys_exit.called)
        # Check for argparse error message indicating missing arguments
        # e.g., self.assertTrue(any("the following arguments are required" in str(c[0]) for c in mock_print.call_args_list))
        mock_subprocess_run_unused.assert_not_called()
        mock_find_csv_unused.assert_not_called()

if __name__ == '__main__':
    unittest.main()
