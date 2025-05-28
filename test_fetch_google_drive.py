import unittest
from unittest.mock import patch, mock_open, MagicMock, call
import sys
import os
import io

# Attempt to import the module to be tested.
# If fetch_google_drive.py doesn't exist or has import errors, these tests will largely fail at runtime,
# but they are being created based on the specification.
try:
    from fetch_google_drive import get_credentials, download_file, main as fetch_main
    # Assuming HttpError might be imported or accessible for error handling tests
    from googleapiclient.errors import HttpError
    from google.auth.exceptions import RefreshError, DefaultCredentialsError
except ImportError as e:
    print(f"Note: Could not import from fetch_google_drive: {e}. Tests will proceed with mocks.")
    # Define dummy exceptions if import fails, so tests can be syntactically correct
    class HttpError(Exception): pass
    class RefreshError(Exception): pass
    class DefaultCredentialsError(Exception): pass
    get_credentials = MagicMock()
    download_file = MagicMock()
    fetch_main = MagicMock()


# Mock for google.oauth2.credentials.Credentials
class MockCredentials:
    def __init__(self, token="mock_token", valid=True, expired=False, refresh_token="mock_refresh_token"):
        self.token = token
        self.valid = valid
        self.expired = expired
        self.refresh_token = refresh_token

    def refresh(self, request):
        if self.refresh_token:
            self.expired = False
            self.valid = True
        else:
            raise RefreshError("No refresh token")

    @classmethod
    def from_authorized_user_file(cls, filename, scopes):
        if os.path.exists(filename): # Simulate loading
            return cls() 
        raise FileNotFoundError


# Mock for google_auth_oauthlib.flow.InstalledAppFlow
class MockInstalledAppFlow:
    def __init__(self, client_secrets_file, scopes):
        self.client_secrets_file = client_secrets_file
        self.scopes = scopes
        if not os.path.exists(client_secrets_file):
             raise FileNotFoundError(f"{client_secrets_file} not found")


    def run_local_server(self, port=0):
        return MockCredentials(token="new_mock_token")

    @classmethod
    def from_client_secrets_file(cls, client_secrets_file, scopes):
        return cls(client_secrets_file, scopes)
        

# Mock for googleapiclient.http.MediaIoBaseDownload
class MockMediaIoBaseDownload:
    def __init__(self, fh, request, chunksize=1024*1024):
        self.fh = fh
        self.request = request # This would be the mock response from service.files().get_media() or export_media()
        self.chunksize = chunksize
        self._done = False 
        # Simulate some content to be "downloaded"
        self.simulated_content = b"This is a test file content." 
        self.bytes_written = 0


    def next_chunk(self):
        if not self._done:
            if self.bytes_written < len(self.simulated_content):
                # Simulate writing chunk by chunk
                chunk = self.simulated_content[self.bytes_written : self.bytes_written + 10] # Small chunk for testing
                self.fh.write(chunk)
                self.bytes_written += len(chunk)
                if self.bytes_written >= len(self.simulated_content):
                    self._done = True
                return (None, self._done) # (status, done)
            else: # Should not happen if logic is correct
                 self._done = True
                 return (None, self._done)
        return (None, self._done)


class TestFetchGoogleDrive(unittest.TestCase):

    SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

    @patch('fetch_google_drive.os.path.exists')
    @patch('fetch_google_drive.Credentials.from_authorized_user_file', new_callable=lambda: MockCredentials.from_authorized_user_file)
    def test_get_credentials_token_exists_valid(self, mock_creds_from_file, mock_os_exists):
        """Test get_credentials when token.json exists and is valid."""
        mock_os_exists.return_value = True # token.json exists
        # MockCredentials.from_authorized_user_file is already set up to return a valid mock credential
        
        # Simulate that the loaded credentials are valid
        mock_valid_creds = MockCredentials(valid=True, expired=False)
        mock_creds_from_file.return_value = mock_valid_creds
        
        # In fetch_google_drive, Credentials might be imported as from google.oauth2.credentials import Credentials
        # So, the patch target might need to be 'fetch_google_drive.Credentials'
        # For now, assuming 'Credentials' is directly available or aliased in the module.
        # This test assumes get_credentials checks creds.valid and creds.expired

        with patch('fetch_google_drive.Credentials', MockCredentials): # Ensure our mock Creds is used
             creds = get_credentials()

        self.assertIsNotNone(creds)
        self.assertTrue(creds.valid)
        self.assertFalse(creds.expired)
        mock_os_exists.assert_called_once_with('token.json')
        # This assertion needs to align with how `from_authorized_user_file` is called in the actual module
        # Assuming SCOPES is defined and used in get_credentials
        # mock_creds_from_file.assert_called_once_with('token.json', self.SCOPES)


    @patch('fetch_google_drive.os.path.exists')
    @patch('fetch_google_drive.Credentials.from_authorized_user_file') # Will raise FileNotFoundError if token.json doesn't exist
    @patch('fetch_google_drive.InstalledAppFlow.from_client_secrets_file', new_callable=lambda: MockInstalledAppFlow.from_client_secrets_file)
    @patch('builtins.open', new_callable=mock_open)
    @patch('json.dump')
    def test_get_credentials_token_does_not_exist(self, mock_json_dump, mock_open_file, 
                                                 mock_flow_from_secrets, mock_creds_from_file, mock_os_exists):
        """Test get_credentials when token.json does not exist."""
        mock_os_exists.return_value = False # token.json does not exist
        mock_creds_from_file.side_effect = FileNotFoundError # Simulate token.json not loadable

        # Mock the flow to return new credentials
        mock_new_creds = MockCredentials(token="new_token")
        # This relies on MockInstalledAppFlow.run_local_server returning mock_new_creds
        # And that from_client_secrets_file returns an instance of MockInstalledAppFlow
        
        # Need to ensure that the flow object returned by from_client_secrets_file
        # has a run_local_server method that returns our mock_new_creds
        mock_flow_instance = MockInstalledAppFlow("credentials.json", self.SCOPES)
        mock_flow_instance.run_local_server = MagicMock(return_value=mock_new_creds)
        mock_flow_from_secrets.return_value = mock_flow_instance

        with patch('fetch_google_drive.InstalledAppFlow', MockInstalledAppFlow): # Ensure our mock Flow is used
            creds = get_credentials()

        self.assertIsNotNone(creds)
        self.assertEqual(creds.token, "new_token")
        mock_os_exists.assert_called_once_with('token.json')
        mock_flow_from_secrets.assert_called_once_with('credentials.json', self.SCOPES)
        mock_flow_instance.run_local_server.assert_called_once_with(port=0)
        mock_open_file.assert_called_once_with('token.json', 'w')
        # json.dump would be called with an object that represents credentials.token, not the object itself
        # This needs to match what fetch_google_drive.py actually saves.
        # Assuming it saves something like {'token': creds.token, 'refresh_token': creds.refresh_token, ...}
        # For simplicity, we'll just check it was called.
        self.assertTrue(mock_json_dump.called)


    @patch('fetch_google_drive.os.path.exists', return_value=False) # token.json does not exist
    @patch('fetch_google_drive.Credentials.from_authorized_user_file', side_effect=FileNotFoundError)
    @patch('fetch_google_drive.InstalledAppFlow.from_client_secrets_file', side_effect=FileNotFoundError("credentials.json not found"))
    def test_get_credentials_credentials_json_missing(self, mock_flow_from_secrets, mock_creds_from_file, mock_os_exists):
        """Test get_credentials when credentials.json is missing."""
        with self.assertRaises(FileNotFoundError) as context: # Or expect sys.exit(1) if that's how it's handled
            get_credentials()
        self.assertIn("credentials.json not found", str(context.exception))


    @patch('fetch_google_drive.build') # Mock build('drive', 'v3', credentials=...)
    @patch('fetch_google_drive.MediaIoBaseDownload', new=MockMediaIoBaseDownload) # Replace with our mock
    @patch('builtins.open', new_callable=mock_open)
    def test_download_file_regular_success(self, mock_open_file, mock_build_drive):
        """Test regular file download (no MIME type)."""
        mock_credentials = MockCredentials()
        mock_service = MagicMock()
        mock_build_drive.return_value = mock_service
        
        # Mock the response from service.files().get_media()
        # This should be a mock object that can be passed to MediaIoBaseDownload
        mock_media_request = MagicMock() # This represents the request object from get_media
        mock_service.files().get_media.return_value = mock_media_request

        file_id = "test_file_id"
        destination_path = "downloaded_file.txt"

        download_file(mock_credentials, file_id, destination_path)

        mock_build_drive.assert_called_once_with('drive', 'v3', credentials=mock_credentials)
        mock_service.files().get_media.assert_called_once_with(fileId=file_id)
        mock_open_file.assert_called_once_with(destination_path, 'wb')
        
        # Check content written (via MockMediaIoBaseDownload's behavior)
        # mock_open_file().write.assert_any_call(MockMediaIoBaseDownload.simulated_content)
        # MockMediaIoBaseDownload writes in chunks, so check for parts or final content
        written_content = b"".join(call_args[0][0] for call_args in mock_open_file().write.call_args_list)
        self.assertEqual(written_content, MockMediaIoBaseDownload(None,None).simulated_content)


    @patch('fetch_google_drive.build')
    @patch('fetch_google_drive.MediaIoBaseDownload', new=MockMediaIoBaseDownload)
    @patch('builtins.open', new_callable=mock_open)
    def test_download_file_export_success(self, mock_open_file, mock_build_drive):
        """Test file export with a specified MIME type."""
        mock_credentials = MockCredentials()
        mock_service = MagicMock()
        mock_build_drive.return_value = mock_service

        mock_media_request = MagicMock()
        mock_service.files().export_media.return_value = mock_media_request
        
        file_id = "test_gdoc_id"
        destination_path = "exported_file.pdf"
        mime_type = "application/pdf"

        download_file(mock_credentials, file_id, destination_path, mime_type=mime_type)

        mock_build_drive.assert_called_once_with('drive', 'v3', credentials=mock_credentials)
        mock_service.files().export_media.assert_called_once_with(fileId=file_id, mimeType=mime_type)
        mock_open_file.assert_called_once_with(destination_path, 'wb')
        written_content = b"".join(call_args[0][0] for call_args in mock_open_file().write.call_args_list)
        self.assertEqual(written_content, MockMediaIoBaseDownload(None,None).simulated_content)


    @patch('fetch_google_drive.build')
    @patch('builtins.print') # To check for error messages
    def test_download_file_google_api_http_error(self, mock_print, mock_build_drive):
        """Test handling of HttpError from Google Drive API."""
        mock_credentials = MockCredentials()
        mock_service = MagicMock()
        mock_build_drive.return_value = mock_service
        
        # Simulate HttpError from files().get_media()
        # The HttpError needs a response object and content.
        mock_resp = MagicMock()
        mock_resp.status = 404
        mock_resp.reason = "File not found"
        # HttpError(resp, content, uri)
        mock_service.files().get_media.side_effect = HttpError(mock_resp, b"Error content", "uri")


        file_id = "error_file_id"
        destination_path = "error_download.txt"

        # Depending on how fetch_google_drive.py handles errors (e.g. try-except-print, sys.exit, or raise)
        # this test might need adjustment. Assuming it prints and continues or exits gracefully.
        with self.assertRaises(HttpError): # Or assert mock_print was called with error
             download_file(mock_credentials, file_id, destination_path)
        
        # If the function catches HttpError and prints:
        # download_file(mock_credentials, file_id, destination_path)
        # self.assertTrue(mock_print.called)
        # mock_print.assert_any_call(unittest.mock.ANY) # Check for specific error message if possible


    # --- Tests for main entry point ---
    @patch('fetch_google_drive.get_credentials')
    @patch('fetch_google_drive.download_file')
    def run_main_with_args(self, args_list, mock_download_file, mock_get_credentials):
        """Helper to run the main part of the script with mocked sys.argv."""
        mock_creds_instance = MockCredentials()
        mock_get_credentials.return_value = mock_creds_instance
        
        original_argv = sys.argv
        sys.argv = args_list
        
        # This assumes fetch_google_drive.py has a main() function that is called
        # when the script is run.
        # If the script's main logic is directly in `if __name__ == "__main__":`,
        # we would need to exec the script content like in previous test files.
        # For now, assuming a callable `fetch_main()` or `main()` exists.
        try:
            # If fetch_main is the actual main function from the module
            fetch_main() 
        except SystemExit: # Catch sys.exit called by arg parsing errors
            pass
        finally:
            sys.argv = original_argv


    @patch('fetch_google_drive.get_credentials')
    @patch('fetch_google_drive.download_file')
    def test_main_download_regular(self, mock_download_file_func, mock_get_credentials_func):
        """Test main for regular download."""
        args = ["fetch_google_drive.py", "file123", "mydoc.txt"]
        self.run_main_with_args(args, mock_download_file_func, mock_get_credentials_func)
        
        mock_get_credentials_func.assert_called_once()
        creds_used = mock_get_credentials_func.return_value
        mock_download_file_func.assert_called_once_with(creds_used, "file123", "mydoc.txt", None)

    @patch('fetch_google_drive.get_credentials')
    @patch('fetch_google_drive.download_file')
    def test_main_download_with_mime_type(self, mock_download_file_func, mock_get_credentials_func):
        """Test main for download with MIME type (export)."""
        args = ["fetch_google_drive.py", "doc_id_456", "mydoc.pdf", "--mime_type", "application/pdf"]
        self.run_main_with_args(args, mock_download_file_func, mock_get_credentials_func)

        mock_get_credentials_func.assert_called_once()
        creds_used = mock_get_credentials_func.return_value
        mock_download_file_func.assert_called_once_with(creds_used, "doc_id_456", "mydoc.pdf", "application/pdf")

    @patch('fetch_google_drive.get_credentials')
    @patch('fetch_google_drive.download_file')
    @patch('builtins.print') # To capture ArgumentParser error output
    @patch('sys.exit') # To prevent test runner from exiting
    def test_main_missing_arguments(self, mock_sys_exit, mock_print, mock_download_file_func, mock_get_credentials_func):
        """Test main with missing required arguments."""
        args = ["fetch_google_drive.py", "file_only_id"] # Missing destination_path
        self.run_main_with_args(args, mock_download_file_func, mock_get_credentials_func)
        
        # argparse usually prints to stderr, then exits.
        # The exact assertion depends on how argparse is set up in fetch_google_drive.py
        self.assertTrue(mock_print.called or mock_sys_exit.called) # One or both should happen
        mock_download_file_func.assert_not_called()


if __name__ == '__main__':
    # This setup is to make sure the mocks are in place if fetch_google_drive.py
    # is imported at the top level of this test file and tries to use Google API modules.
    # We are essentially pre-patching them for the initial import of fetch_google_drive.
    # This is a bit of a workaround for testing a module that might have top-level API calls
    # or class definitions using API components.

    # Mock google modules that might be imported by fetch_google_drive.py at its top level
    google_mock = MagicMock()
    sys.modules['google'] = google_mock
    sys.modules['google.oauth2'] = MagicMock()
    sys.modules['google.oauth2.credentials'] = MagicMock(Credentials=MockCredentials)
    sys.modules['google_auth_oauthlib'] = MagicMock()
    sys.modules['google_auth_oauthlib.flow'] = MagicMock(InstalledAppFlow=MockInstalledAppFlow)
    sys.modules['googleapiclient'] = MagicMock()
    sys.modules['googleapiclient.discovery'] = MagicMock()
    sys.modules['googleapiclient.http'] = MagicMock(MediaIoBaseDownload=MockMediaIoBaseDownload)
    sys.modules['googleapiclient.errors'] = MagicMock(HttpError=HttpError)
    sys.modules['google.auth.exceptions'] = MagicMock(RefreshError=RefreshError, DefaultCredentialsError=DefaultCredentialsError)
    
    unittest.main()
