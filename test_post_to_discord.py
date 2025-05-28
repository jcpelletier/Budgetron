import unittest
from unittest.mock import patch, mock_open, MagicMock, call
import sys
import os
import json
from post_to_discord import post_to_discord, process_message_with_chatgpt

# Helper to simulate requests.Response
def mock_response(status_code=200, json_data=None, text_data=""):
    res = MagicMock()
    res.status_code = status_code
    res.json.return_value = json_data
    res.text = text_data
    res.raise_for_status = MagicMock()
    if status_code >= 400:
        res.raise_for_status.side_effect = requests.exceptions.HTTPError(f"Mock HTTP Error {status_code}")
    return res

# Need to import requests here for the side_effect above
import requests

class TestPostToDiscord(unittest.TestCase):

    def setUp(self):
        self.bot_token = "test_bot_token"
        self.channel_id = "test_channel_id"
        self.message_text = "Hello Discord!"
        self.image_path = "test_image.png"
        self.chatgpt_api_key = "fake_chatgpt_key"
        self.discord_api_url = f"https://discord.com/api/v10/channels/{self.channel_id}/messages"
        self.openai_api_url = "https://api.openai.com/v1/chat/completions"

    # --- Tests for process_message_with_chatgpt ---
    @patch('post_to_discord.requests.post')
    def test_process_message_with_chatgpt_success(self, mock_requests_post):
        """Test successful ChatGPT processing."""
        chatgpt_response_content = "Processed: " + self.message_text
        mock_requests_post.return_value = mock_response(
            status_code=200,
            json_data={"choices": [{"message": {"content": chatgpt_response_content}}]}
        )

        processed_message = process_message_with_chatgpt(self.chatgpt_api_key, self.message_text)

        self.assertEqual(processed_message, chatgpt_response_content)
        mock_requests_post.assert_called_once()
        args, kwargs = mock_requests_post.call_args
        self.assertEqual(args[0], self.openai_api_url)
        self.assertIn(f"Bearer {self.chatgpt_api_key}", kwargs["headers"]["Authorization"])
        self.assertEqual(kwargs["json"]["messages"][-1]["content"], self.message_text)

    def test_process_message_with_chatgpt_no_api_key(self):
        """Test ChatGPT processing when API key is missing."""
        with self.assertRaises(ValueError) as context:
            process_message_with_chatgpt(None, self.message_text)
        self.assertIn("ChatGPT API key is not set", str(context.exception))

    @patch('post_to_discord.requests.post')
    @patch('builtins.print')
    def test_process_message_with_chatgpt_http_error(self, mock_print, mock_requests_post):
        """Test ChatGPT HTTP error handling."""
        mock_requests_post.return_value = mock_response(status_code=500, text_data="Server Error")
        mock_requests_post.return_value.raise_for_status.side_effect = requests.exceptions.HTTPError("Mock HTTP Error")

        message = process_message_with_chatgpt(self.chatgpt_api_key, self.message_text)
        
        self.assertEqual(message, self.message_text) # Should fallback to original
        mock_print.assert_any_call(unittest.mock.ANY) # Check if any print happened for the error

    @patch('post_to_discord.requests.post')
    @patch('builtins.print')
    def test_process_message_with_chatgpt_request_exception(self, mock_print, mock_requests_post):
        """Test ChatGPT request exception handling."""
        mock_requests_post.side_effect = requests.exceptions.RequestException("Mock Request Error")

        message = process_message_with_chatgpt(self.chatgpt_api_key, self.message_text)

        self.assertEqual(message, self.message_text) # Should fallback
        mock_print.assert_any_call(unittest.mock.ANY)


    # --- Tests for post_to_discord (core message sending) ---
    @patch('post_to_discord.requests.post')
    @patch('post_to_discord.process_message_with_chatgpt', side_effect=lambda _, msg: msg) # Mock out ChatGPT
    def test_send_simple_text_message_success(self, mock_process_msg, mock_requests_post):
        """Test sending a simple text message successfully."""
        mock_requests_post.return_value = mock_response(status_code=200)

        post_to_discord(self.bot_token, self.channel_id, self.message_text)

        mock_requests_post.assert_called_once()
        args, kwargs = mock_requests_post.call_args
        self.assertEqual(args[0], self.discord_api_url)
        self.assertEqual(kwargs["headers"]["Authorization"], f"Bot {self.bot_token}")
        self.assertEqual(kwargs["json"]["content"], self.message_text)
        self.assertNotIn("files", kwargs)

    @patch('post_to_discord.os.path.isfile', return_value=True)
    @patch('builtins.open', new_callable=mock_open, read_data=b"imagedata")
    @patch('post_to_discord.requests.post')
    @patch('post_to_discord.process_message_with_chatgpt', side_effect=lambda _, msg: msg)
    def test_send_message_with_image_success(self, mock_process_msg, mock_requests_post, mock_file_open, mock_isfile):
        """Test sending a message with an image successfully."""
        mock_requests_post.return_value = mock_response(status_code=200)

        post_to_discord(self.bot_token, self.channel_id, self.message_text, image_path=self.image_path)

        mock_isfile.assert_called_once_with(self.image_path)
        mock_file_open.assert_called_once_with(self.image_path, "rb")
        mock_requests_post.assert_called_once()
        args, kwargs = mock_requests_post.call_args
        self.assertEqual(args[0], self.discord_api_url)
        self.assertIn(f"Bot {self.bot_token}", kwargs["headers"]["Authorization"])
        # When files are present, data is sent as form data with 'payload_json'
        self.assertIn("payload_json", kwargs["data"])
        self.assertEqual(json.loads(kwargs["data"]["payload_json"])["content"], self.message_text)
        self.assertIn("files", kwargs)
        self.assertTrue(hasattr(kwargs["files"]["file"], "read"))


    @patch('post_to_discord.requests.post')
    @patch('post_to_discord.process_message_with_chatgpt', side_effect=lambda _, msg: msg)
    @patch('builtins.print') # To capture error prints
    def test_send_message_discord_api_http_error(self, mock_print, mock_process_msg, mock_requests_post):
        """Test handling of Discord API HTTP errors."""
        mock_requests_post.return_value = mock_response(status_code=400, text_data="Bad Request")
        # Manually trigger the side effect for raise_for_status
        mock_requests_post.return_value.raise_for_status.side_effect = requests.exceptions.HTTPError("Mock HTTP Error 400")


        post_to_discord(self.bot_token, self.channel_id, self.message_text)
        
        mock_requests_post.assert_called_once()
        # Check that error messages were printed
        self.assertTrue(any("HTTP error" in call_args[0][0] for call_args in mock_print.call_args_list if call_args[0]))


    @patch('post_to_discord.requests.post')
    @patch('post_to_discord.process_message_with_chatgpt', side_effect=lambda _, msg: msg)
    @patch('builtins.print')
    def test_send_message_discord_api_request_exception(self, mock_print, mock_process_msg, mock_requests_post):
        """Test handling of Discord API request exceptions."""
        mock_requests_post.side_effect = requests.exceptions.RequestException("Mock Request Error")

        post_to_discord(self.bot_token, self.channel_id, self.message_text)

        mock_requests_post.assert_called_once()
        self.assertTrue(any("Request error" in call_args[0][0] for call_args in mock_print.call_args_list if call_args[0]))

    @patch('post_to_discord.os.path.isfile', return_value=False)
    @patch('builtins.print')
    @patch('sys.exit') # Mock sys.exit to prevent test runner from stopping
    def test_send_message_with_non_existent_image(self, mock_sys_exit, mock_print, mock_isfile):
        """Test sending a message when image_path does not exist."""
        post_to_discord(self.bot_token, self.channel_id, self.message_text, image_path="non_existent.png")

        mock_isfile.assert_called_once_with("non_existent.png")
        mock_print.assert_any_call("Error: File 'non_existent.png' not found.")
        mock_sys_exit.assert_called_once_with(1)

    # --- Tests for post_to_discord (with ChatGPT integration) ---
    @patch.dict(os.environ, {"CHATGPT_API_KEY": "fake_key_for_test"})
    @patch('post_to_discord.requests.post') # This will mock both Discord and OpenAI calls
    def test_send_message_with_chatgpt_success(self, mock_requests_post):
        """Test successful message sending with ChatGPT processing."""
        chatgpt_processed_text = "ChatGPT says: " + self.message_text
        
        # Setup responses: first for ChatGPT, second for Discord
        mock_requests_post.side_effect = [
            mock_response(status_code=200, json_data={"choices": [{"message": {"content": chatgpt_processed_text}}]}), # OpenAI
            mock_response(status_code=200) # Discord
        ]

        post_to_discord(self.bot_token, self.channel_id, self.message_text, use_chatgpt=True)

        self.assertEqual(mock_requests_post.call_count, 2)
        
        # OpenAI call assertions
        openai_call_args, openai_call_kwargs = mock_requests_post.call_args_list[0]
        self.assertEqual(openai_call_args[0], self.openai_api_url)
        self.assertIn(f"Bearer fake_key_for_test", openai_call_kwargs["headers"]["Authorization"])
        
        # Discord call assertions
        discord_call_args, discord_call_kwargs = mock_requests_post.call_args_list[1]
        self.assertEqual(discord_call_args[0], self.discord_api_url)
        self.assertEqual(discord_call_kwargs["json"]["content"], chatgpt_processed_text)


    @patch.dict(os.environ, {}, clear=True) # Ensure CHATGPT_API_KEY is not set
    @patch('builtins.print')
    @patch('sys.exit')
    def test_send_message_with_chatgpt_no_api_key_env(self, mock_sys_exit, mock_print):
        """Test message sending with ChatGPT when CHATGPT_API_KEY is not set."""
        post_to_discord(self.bot_token, self.channel_id, self.message_text, use_chatgpt=True)
        
        mock_print.assert_any_call("Error: ChatGPT API key is not set. Please set the CHATGPT_API_KEY environment variable.")
        mock_sys_exit.assert_called_once_with(1)


    # --- Tests for __main__ entry point ---
    # Helper to run the __main__ block of post_to_discord.py by executing it.
    def run_main_with_args(self, args_list, mock_post_to_discord_func):
        original_argv = sys.argv
        sys.argv = args_list
        script_path = "post_to_discord.py" # Assumes script is in current dir or discoverable
        try:
            with open(script_path, 'r') as f:
                script_code = f.read()
            # Execute with mocks in place for the functions called by __main__
            exec_globals = {
                '__name__': '__main__', 
                'sys': sys, # Our patched sys
                'os': os,   # Our patched os (if needed for os.path.exists in __main__)
                'post_to_discord': mock_post_to_discord_func, # Mock the core function
                'requests': MagicMock(), # Mock requests if __main__ uses it directly (it doesn't)
                'json': json,
            }
            exec(script_code, exec_globals)
        finally:
            sys.argv = original_argv

    @patch('post_to_discord.post_to_discord') # Mock the core function called by __main__
    @patch('sys.exit') # Prevent tests from exiting
    @patch('builtins.print') # Capture print output
    def test_main_entry_simple_message(self, mock_print, mock_sys_exit, mock_post_func):
        args = ["script.py", self.bot_token, self.channel_id, self.message_text]
        self.run_main_with_args(args, mock_post_func)
        mock_post_func.assert_called_once_with(self.bot_token, self.channel_id, self.message_text, False, None)

    @patch('post_to_discord.post_to_discord')
    @patch('sys.exit')
    @patch('builtins.print')
    def test_main_entry_message_with_image(self, mock_print, mock_sys_exit, mock_post_func):
        # Order: token id msg image_path
        args = ["script.py", self.bot_token, self.channel_id, self.message_text, self.image_path]
        self.run_main_with_args(args, mock_post_func)
        mock_post_func.assert_called_once_with(self.bot_token, self.channel_id, self.message_text, False, self.image_path)

    @patch('post_to_discord.post_to_discord')
    @patch('sys.exit')
    @patch('builtins.print')
    def test_main_entry_message_with_chatgpt_flag(self, mock_print, mock_sys_exit, mock_post_func):
        # Order: token id msg --use_chatgpt
        args = ["script.py", self.bot_token, self.channel_id, self.message_text, "--use_chatgpt"]
        self.run_main_with_args(args, mock_post_func)
        mock_post_func.assert_called_once_with(self.bot_token, self.channel_id, self.message_text, True, None)

    @patch('post_to_discord.post_to_discord')
    @patch('sys.exit')
    @patch('builtins.print')
    def test_main_entry_message_with_chatgpt_flag_and_image(self, mock_print, mock_sys_exit, mock_post_func):
        # Order: token id msg --use_chatgpt image_path
        args = ["script.py", self.bot_token, self.channel_id, self.message_text, "--use_chatgpt", self.image_path]
        self.run_main_with_args(args, mock_post_func)
        mock_post_func.assert_called_once_with(self.bot_token, self.channel_id, self.message_text, True, self.image_path)

    @patch('post_to_discord.post_to_discord')
    @patch('sys.exit')
    @patch('builtins.print')
    def test_main_entry_message_with_image_and_chatgpt_flag_alternative_order(self, mock_print, mock_sys_exit, mock_post_func):
        # Order: token id msg image_path --use_chatgpt
        # Based on script's logic, this will NOT correctly identify image_path. image_path will be None.
        args = ["script.py", self.bot_token, self.channel_id, self.message_text, self.image_path, "--use_chatgpt"]
        self.run_main_with_args(args, mock_post_func)
        # The script's __main__ will incorrectly parse image_path as None here.
        mock_post_func.assert_called_once_with(self.bot_token, self.channel_id, self.message_text, True, None)


    @patch('post_to_discord.post_to_discord') # Won't be called
    @patch('sys.exit')
    @patch('builtins.print')
    def test_main_entry_insufficient_args(self, mock_print, mock_sys_exit, mock_post_func):
        args = ["script.py", self.bot_token, self.channel_id] # Missing message
        self.run_main_with_args(args, mock_post_func)
        mock_print.assert_any_call("Usage: python post_to_discord.py <bot_token> <channel_id> <message> [--use_chatgpt] [<image_path>]")
        mock_sys_exit.assert_called_once_with(1)
        mock_post_func.assert_not_called()
        
if __name__ == '__main__':
    unittest.main()
