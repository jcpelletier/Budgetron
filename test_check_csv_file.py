import unittest
from unittest.mock import patch, mock_open, MagicMock
import os
import datetime
from check_csv_file import find_csv_for_current_month, send_discord_notification, main # Updated imports
import argparse

class TestCheckCsvFile(unittest.TestCase):

    @patch('check_csv_file.glob.glob') # Mocking glob.glob used by find_csv_for_current_month
    def test_find_csv_for_current_month_found(self, mock_glob):
        """Test that the CSV is found when it exists."""
        now = datetime.datetime.now()
        month_year_str = now.strftime("%B %Y")
        expected_filename = f"{month_year_str} - something.csv"
        mock_glob.return_value = [expected_filename] # Simulate file found

        found, month, year = find_csv_for_current_month(folder_path="dummy_folder")

        self.assertTrue(found)
        self.assertEqual(month, now.strftime("%B"))
        self.assertEqual(year, now.strftime("%Y"))
        mock_glob.assert_called_once_with(os.path.join("dummy_folder", f"{now.strftime('%B')} {now.strftime('%Y')} -*.csv"))

    @patch('check_csv_file.glob.glob')
    def test_find_csv_for_current_month_not_found(self, mock_glob):
        """Test that the CSV is not found when it does not exist."""
        mock_glob.return_value = [] # Simulate file not found

        now = datetime.datetime.now()
        found, month, year = find_csv_for_current_month(folder_path="dummy_folder")

        self.assertFalse(found)
        self.assertEqual(month, now.strftime("%B")) # Month and year are still returned
        self.assertEqual(year, now.strftime("%Y"))
        mock_glob.assert_called_once_with(os.path.join("dummy_folder", f"{now.strftime('%B')} {now.strftime('%Y')} -*.csv"))
    
    @patch('check_csv_file.glob.glob')
    def test_find_csv_for_current_month_exception(self, mock_glob):
        """Test exception handling in find_csv_for_current_month."""
        mock_glob.side_effect = Exception("Test exception")

        found, month, year = find_csv_for_current_month(folder_path="dummy_folder")

        self.assertFalse(found)
        self.assertIsNone(month)
        self.assertIsNone(year)

    @patch('check_csv_file.subprocess.run') # Mocking subprocess.run used by send_discord_notification
    def test_send_discord_notification_success(self, mock_subprocess_run):
        """Test that Discord notification is sent successfully."""
        send_discord_notification(bot_token="fake_token", channel_id="fake_channel", message="Test message")
        
        expected_command = ["python", "post_to_discord.py", "fake_token", "fake_channel", "Test message"]
        mock_subprocess_run.assert_called_once_with(expected_command, check=True)

    @patch('check_csv_file.subprocess.run')
    def test_send_discord_notification_failure(self, mock_subprocess_run):
        """Test failure in sending Discord notification."""
        mock_subprocess_run.side_effect = subprocess.CalledProcessError(1, "cmd")
        
        # We expect send_discord_notification to catch the exception and print an error
        # For this test, we just ensure it's called. How it handles the error (e.g. logging) can be checked if needed.
        send_discord_notification(bot_token="fake_token", channel_id="fake_channel", message="Test message")
        
        expected_command = ["python", "post_to_discord.py", "fake_token", "fake_channel", "Test message"]
        mock_subprocess_run.assert_called_once_with(expected_command, check=True)

    @patch('check_csv_file.argparse.ArgumentParser.parse_args')
    @patch('check_csv_file.find_csv_for_current_month')
    @patch('check_csv_file.send_discord_notification')
    def test_main_function_file_found(self, mock_send_notification, mock_find_csv, mock_parse_args):
        """Test the main function when a CSV file is found."""
        # Mock command line arguments
        mock_parse_args.return_value = argparse.Namespace(folder="dummy_folder", bot_token="fake_token", channel_id="fake_channel")
        
        # Mock find_csv_for_current_month to simulate file found
        now = datetime.datetime.now()
        current_month_str = now.strftime("%B")
        current_year_str = now.strftime("%Y")
        mock_find_csv.return_value = (True, current_month_str, current_year_str)

        main()

        mock_find_csv.assert_called_once_with("dummy_folder")
        expected_message = f"The CSV file for month: {current_month_str} and year: {current_year_str} was found."
        mock_send_notification.assert_called_once_with("fake_token", "fake_channel", expected_message)

    @patch('check_csv_file.argparse.ArgumentParser.parse_args')
    @patch('check_csv_file.find_csv_for_current_month')
    @patch('check_csv_file.send_discord_notification')
    def test_main_function_file_not_found(self, mock_send_notification, mock_find_csv, mock_parse_args):
        """Test the main function when a CSV file is not found."""
        mock_parse_args.return_value = argparse.Namespace(folder="dummy_folder", bot_token="fake_token", channel_id="fake_channel")
        
        now = datetime.datetime.now()
        current_month_str = now.strftime("%B")
        current_year_str = now.strftime("%Y")
        mock_find_csv.return_value = (False, current_month_str, current_year_str) # Simulate file not found

        main()

        mock_find_csv.assert_called_once_with("dummy_folder")
        expected_message = f"The CSV file for month: {current_month_str} and year: {current_year_str} was not found."
        mock_send_notification.assert_called_once_with("fake_token", "fake_channel", expected_message)

    # The original tests for folder not found and specific file names are slightly different
    # because check_csv_file.py uses glob for a pattern, not os.listdir for specific names,
    # and it doesn't explicitly check for folder existence before calling glob.
    # glob will return an empty list if the folder doesn't exist or no files match,
    # so the "folder not found" case is effectively handled by the "file not found" logic.
    # If specific behavior for "folder not found" vs "file not found in existing folder" is needed,
    # check_csv_file.py would need to be modified to include an os.path.exists check for the folder.

if __name__ == '__main__':
    unittest.main()
