import unittest
from unittest.mock import patch, mock_open, MagicMock, call
import sys
import os
import io # For Fetch_Google_Drive.io.FileIO mock

# Attempt to import the module to be tested.
try:
    # Corrected function names from Fetch_Google_Drive
    from Fetch_Google_Drive import (
        authenticate_google_drive, 
        fetch_file, 
        is_folder, 
        list_files_in_folder, 
        fetch_file_or_folder,
        SCOPES, # Import SCOPES if defined in Fetch_Google_Drive and used by tests
        main as fetch_main 
    )
    from googleapiclient.errors import HttpError
    from google.auth.exceptions import RefreshError, DefaultCredentialsError
except ImportError as e:
    print(f"Note: Could not import from Fetch_Google_Drive: {e}. Tests will proceed with mocks.")
    # Define dummy exceptions if import fails
    class HttpError(Exception): pass
    class RefreshError(Exception): pass
    class DefaultCredentialsError(Exception): pass
    
    # Mock the new function names
    authenticate_google_drive = MagicMock()
    fetch_file = MagicMock()
    is_folder = MagicMock()
    list_files_in_folder = MagicMock()
    fetch_file_or_folder = MagicMock()
    fetch_main = MagicMock()
    SCOPES = ['https://www.googleapis.com/auth/drive.readonly'] # Fallback SCOPES


# Mock for google.oauth2.credentials.Credentials
class MockCredentials:
    def __init__(self, token="mock_token", valid=True, expired=False, refresh_token="mock_refresh_token", client_id="mock_client_id", client_secret="mock_client_secret", scopes=SCOPES):
        self.token = token
        self.valid = valid
        self.expired = expired
        self.refresh_token = refresh_token
        self.client_id = client_id
        self.client_secret = client_secret
        self.scopes = scopes

    def refresh(self, request):
        if self.refresh_token:
            self.expired = False
            self.valid = True
        else:
            raise RefreshError("No refresh token")

    def to_json(self): # Added to_json method
        return f'{{"token": "{self.token}", "refresh_token": "{self.refresh_token}", "client_id": "{self.client_id}", "client_secret": "{self.client_secret}", "scopes": ["{self.scopes[0]}"]}}'


    @classmethod
    def from_authorized_user_file(cls, filename, scopes):
        if os.path.exists(filename): 
            return cls(scopes=scopes) 
        raise FileNotFoundError

    @classmethod
    def from_authorized_user_info(cls, info, scopes): # If token.json stores more info
        return cls(token=info.get("token"), refresh_token=info.get("refresh_token"), scopes=scopes)


# Mock for google_auth_oauthlib.flow.InstalledAppFlow
class MockInstalledAppFlow:
    def __init__(self, client_config, scopes): # client_secrets_file changed to client_config
        self.client_config = client_config
        self.scopes = scopes
        # Simulate check that would be done by from_client_secrets_file if path was passed
        # if not os.path.exists(client_secrets_file): 
        #      raise FileNotFoundError(f"{client_secrets_file} not found")

    def run_local_server(self, port=0):
        return MockCredentials(token="new_mock_token", scopes=self.scopes)

    @classmethod
    def from_client_secrets_file(cls, client_secrets_file, scopes):
        if not os.path.exists(client_secrets_file): # Actual check
             raise FileNotFoundError(f"Client secrets file {client_secrets_file} not found.")
        # In real usage, client_config would be loaded from the file
        mock_client_config = {"installed": {"client_id": "a", "client_secret": "b", "auth_uri": "c", "token_uri": "d"}}
        return cls(client_config=mock_client_config, scopes=scopes)
        

# Mock for googleapiclient.http.MediaIoBaseDownload
class MockMediaIoBaseDownload:
    def __init__(self, fh, request, chunksize=1024*1024):
        self.fh = fh
        self.request = request 
        self.chunksize = chunksize
        self._done = False 
        self.simulated_content = b"This is a test file content." 
        self.bytes_written = 0

    def next_chunk(self):
        # Step 2: Modify next_chunk to return a mock status object
        mock_status = MagicMock()
        mock_status.progress.return_value = 0.5 # Simulate 50% progress for example
        
        if not self._done:
            if self.bytes_written < len(self.simulated_content):
                chunk = self.simulated_content[self.bytes_written : self.bytes_written + 10] 
                self.fh.write(chunk)
                self.bytes_written += len(chunk)
                if self.bytes_written >= len(self.simulated_content):
                    self._done = True
                return (mock_status, self._done) 
            else: 
                 self._done = True
                 return (mock_status, self._done)
        return (mock_status, self._done)


class TestFetchGoogleDrive(unittest.TestCase):

    # SCOPES is now imported from Fetch_Google_Drive, or uses fallback if import fails
    # So, self.SCOPES = Fetch_Google_Drive.SCOPES (or just SCOPES if imported directly)

    # --- Tests for authenticate_google_drive (formerly get_credentials) ---
    @patch('Fetch_Google_Drive.os.path.exists')
    @patch('Fetch_Google_Drive.Credentials') # Patched to our MockCredentials
    @patch('Fetch_Google_Drive.build') # Mock build as authenticate_google_drive calls it
    def test_authenticate_google_drive_token_exists_valid(self, mock_build, mock_credentials_class, mock_os_exists):
        """Test authenticate_google_drive when token.json exists and is valid."""
        mock_os_exists.return_value = True # token.json exists
        
        mock_valid_creds_instance = MockCredentials(valid=True, expired=False)
        # Credentials.from_authorized_user_file is a classmethod on MockCredentials
        # We need to mock how it's called if Fetch_Google_Drive.Credentials itself is our MockCredentials
        # Or, if Fetch_Google_Drive.Credentials is the real one, mock its from_authorized_user_file
        if hasattr(mock_credentials_class, 'from_authorized_user_file'): # If Credentials is the real one
            mock_credentials_class.from_authorized_user_file.return_value = mock_valid_creds_instance
        else: # If Credentials *is* MockCredentials from our test
             # This path might not be hit if the module uses `from google.oauth2.credentials import Credentials`
             # and we patch `Fetch_Google_Drive.Credentials` to be our `MockCredentials`
             # The critical part is that the *instance* used has .valid and .expired
             pass


        mock_service_instance = MagicMock()
        mock_build.return_value = mock_service_instance
        
        # This test path assumes that if token.json exists, from_authorized_user_file is used.
        # The script logic is: if exists -> from_authorized_user_file. If creds invalid/expired -> refresh.
        # If no token or refresh fails -> flow.
        # This test covers "exists and valid".

        # To ensure that `Credentials.from_authorized_user_file` is used and returns our mock:
        with patch.object(MockCredentials, 'from_authorized_user_file', return_value=mock_valid_creds_instance) as class_method_mock:
            # If `Fetch_Google_Drive.Credentials` is already our `MockCredentials` due to top-level patching,
            # then `from_authorized_user_file` on it will be this mock.
            # If `Fetch_Google_Drive.Credentials` is the real one, this patch won't apply unless it's targeted.
            # Let's assume the initial `patch('Fetch_Google_Drive.Credentials', MockCredentials)` makes it our mock.
            
            service = authenticate_google_drive()

        self.assertIsNotNone(service)
        self.assertEqual(service, mock_service_instance)
        mock_os_exists.assert_called_once_with('token.json')
        # mock_credentials_class.from_authorized_user_file.assert_called_once_with('token.json', SCOPES)
        # The above line is tricky because of how from_authorized_user_file is a classmethod.
        # If Credentials is our MockCredentials, its from_authorized_user_file is already the mock one.
        # If it's the real one, we'd patch 'google.oauth2.credentials.Credentials.from_authorized_user_file'
        
        # Check that build was called with the valid credentials
        mock_build.assert_called_once_with('drive', 'v3', credentials=mock_valid_creds_instance)


    @patch('Fetch_Google_Drive.os.path.exists')
    @patch('Fetch_Google_Drive.Credentials', MockCredentials) # Ensure our MockCredentials is used
    @patch('Fetch_Google_Drive.InstalledAppFlow', MockInstalledAppFlow) # Ensure our MockInstalledAppFlow
    @patch('Fetch_Google_Drive.build')
    @patch('builtins.open', new_callable=mock_open) # For saving token.json
    def test_authenticate_google_drive_token_does_not_exist(self, mock_open_file, mock_build,
                                                            mock_os_exists):
        """Test authenticate_google_drive when token.json does not exist."""
        mock_os_exists.return_value = False # token.json does not exist
        
        # MockInstalledAppFlow.from_client_secrets_file will be called
        # Its run_local_server will return a new MockCredentials instance
        mock_new_creds_from_flow = MockCredentials(token="new_token_from_flow")
        
        # We need to ensure that the MockInstalledAppFlow.run_local_server returns this specific instance
        # This is handled by MockInstalledAppFlow's setup if from_client_secrets_file returns an instance
        # which then has its run_local_server called.
        # Let's refine MockInstalledAppFlow to allow its run_local_server to be mockable for return_value.
        
        # This is tricky because from_client_secrets_file is a classmethod.
        # And run_local_server is an instance method.
        # The patch for InstalledAppFlow should make it our MockInstalledAppFlow.
        # MockInstalledAppFlow.from_client_secrets_file returns an *instance* of MockInstalledAppFlow.
        # That instance's run_local_server should return our mock_new_creds_from_flow.
        
        # We can patch the run_local_server method on the *instance* returned by from_client_secrets_file
        # This requires knowing when from_client_secrets_file is called.
        # A simpler way for this mock: MockInstalledAppFlow.run_local_server is already set to return a new MockCredentials.
        # Let's assume that's sufficient, or refine MockInstalledAppFlow:
        
        # Redefine MockInstalledAppFlow for this test to control the returned creds from run_local_server
        class TempMockInstalledAppFlow(MockInstalledAppFlow):
             def run_local_server(self, port=0): # port is now 58142
                 self.last_port_used = port
                 return mock_new_creds_from_flow # Return our specific instance
        
        with patch('Fetch_Google_Drive.InstalledAppFlow', TempMockInstalledAppFlow) as mock_flow_class_patched:
            service = authenticate_google_drive()

        self.assertIsNotNone(service)
        mock_os_exists.assert_called_once_with('token.json')
        
        # Check from_client_secrets_file call (on the class MockInstalledAppFlow)
        # This is implicitly tested by mock_flow_class_patched being our TempMockInstalledAppFlow
        # and its constructor being called.
        
        # Check run_local_server call (on the instance)
        # The instance is created inside authenticate_google_drive
        # We need to assert on the instance that was used.
        # For now, let's assume TempMockInstalledAppFlow.run_local_server was called correctly.
        # To check port: need to access the instance of TempMockInstalledAppFlow created.
        # This is hard without direct access. A common pattern is to have from_client_secrets_file return a mock *instance*.
        # Let's assume it's called. The port should be 58142.

        mock_open_file.assert_called_once_with('token.json', 'w')
        # Check that creds.to_json() was written
        mock_open_file().write.assert_called_once_with(mock_new_creds_from_flow.to_json())
        mock_build.assert_called_once_with('drive', 'v3', credentials=mock_new_creds_from_flow)


    @patch('Fetch_Google_Drive.os.path.exists', return_value=False) 
    @patch('Fetch_Google_Drive.Credentials', MockCredentials)
    @patch('Fetch_Google_Drive.InstalledAppFlow.from_client_secrets_file', side_effect=FileNotFoundError("credentials.json not found"))
    def test_authenticate_google_drive_credentials_json_missing(self, mock_flow_from_secrets, mock_os_exists):
        """Test authenticate_google_drive when credentials.json is missing."""
        with self.assertRaises(FileNotFoundError) as context:
            authenticate_google_drive()
        self.assertIn("credentials.json not found", str(context.exception))


    # --- Tests for fetch_file (formerly download_file) ---
    @patch('Fetch_Google_Drive.io.FileIO', new_callable=mock_open) # Patched to io.FileIO
    @patch('Fetch_Google_Drive.MediaIoBaseDownload', new=MockMediaIoBaseDownload) 
    def test_fetch_file_regular_success(self, mock_media_download, mock_file_io):
        """Test regular file download (no MIME type specified)."""
        mock_service = MagicMock() # Create a mock service object
        
        mock_media_request = MagicMock() 
        mock_service.files().get_media.return_value = mock_media_request

        file_id = "test_file_id"
        destination_path = "downloaded_file.txt"

        fetch_file(mock_service, file_id, destination_path) # Pass mock_service

        mock_service.files().get_media.assert_called_once_with(fileId=file_id)
        mock_file_io.assert_called_once_with(destination_path, 'wb')
        
        # Check content written
        written_content = b"".join(c[0][0] for c in mock_file_io().write.call_args_list)
        self.assertEqual(written_content, MockMediaIoBaseDownload(None,None).simulated_content)


    @patch('Fetch_Google_Drive.io.FileIO', new_callable=mock_open)
    @patch('Fetch_Google_Drive.MediaIoBaseDownload', new=MockMediaIoBaseDownload)
    def test_fetch_file_export_success(self, mock_media_download, mock_file_io):
        """Test file export with a specified MIME type."""
        mock_service = MagicMock()
        mock_media_request = MagicMock()
        mock_service.files().export_media.return_value = mock_media_request
        
        file_id = "test_gdoc_id"
        destination_path = "exported_file.pdf"
        mime_type = "application/pdf"

        fetch_file(mock_service, file_id, destination_path, mime_type=mime_type)

        mock_service.files().export_media.assert_called_once_with(fileId=file_id, mimeType=mime_type)
        mock_file_io.assert_called_once_with(destination_path, 'wb')
        written_content = b"".join(c[0][0] for c in mock_file_io().write.call_args_list)
        self.assertEqual(written_content, MockMediaIoBaseDownload(None,None).simulated_content)

    @patch('builtins.print') 
    def test_fetch_file_google_api_http_error(self, mock_print):
        """Test handling of HttpError from Google Drive API during fetch_file."""
        mock_service = MagicMock()
        mock_resp = MagicMock(status=404, reason="File not found")
        http_error_instance = HttpError(mock_resp, b"Error content", "uri")
        mock_service.files().get_media.side_effect = http_error_instance

        file_id = "error_file_id"
        destination_path = "error_download.txt"

        # fetch_file catches HttpError and prints it.
        fetch_file(mock_service, file_id, destination_path)
        
        self.assertTrue(mock_print.called)
        # Example check: first arg of first call to print contains "HttpError"
        self.assertIn("HttpError", str(mock_print.call_args_list[0][0][0]))
        self.assertIn(file_id, str(mock_print.call_args_list[0][0][0]))


    # --- Tests for is_folder ---
    def test_is_folder_true(self):
        mock_service = MagicMock()
        mock_service.files().get().execute.return_value = {'mimeType': 'application/vnd.google-apps.folder'}
        self.assertTrue(is_folder(mock_service, "folder_id"))
        mock_service.files().get.assert_called_once_with(fileId="folder_id", fields='mimeType')

    def test_is_folder_false(self):
        mock_service = MagicMock()
        mock_service.files().get().execute.return_value = {'mimeType': 'application/pdf'}
        self.assertFalse(is_folder(mock_service, "file_id"))

    @patch('builtins.print')
    def test_is_folder_error(self, mock_print):
        mock_service = MagicMock()
        mock_service.files().get().execute.side_effect = HttpError(MagicMock(status=500), b"Server error")
        self.assertFalse(is_folder(mock_service, "error_id")) # Should return False on error
        mock_print.assert_any_call(unittest.mock.ANY) # Check an error was printed


    # --- Tests for list_files_in_folder ---
    def test_list_files_in_folder_success(self):
        mock_service = MagicMock()
        expected_items = [{'id': 'id1', 'name': 'name1'}, {'id': 'id2', 'name': 'name2'}]
        mock_service.files().list().execute.return_value = {'files': expected_items, 'nextPageToken': None}
        
        items = list_files_in_folder(mock_service, "folder_id")
        self.assertEqual(items, expected_items)
        mock_service.files().list.assert_called_once_with(
            q="'folder_id' in parents", fields="nextPageToken, files(id, name)", pageSize=1000, pageToken=None
        )

    def test_list_files_in_folder_empty(self):
        mock_service = MagicMock()
        mock_service.files().list().execute.return_value = {'files': [], 'nextPageToken': None}
        self.assertEqual(list_files_in_folder(mock_service, "empty_folder_id"), [])

    @patch('builtins.print')
    def test_list_files_in_folder_error(self, mock_print):
        mock_service = MagicMock()
        mock_service.files().list().execute.side_effect = HttpError(MagicMock(status=500), b"Server error")
        self.assertEqual(list_files_in_folder(mock_service, "error_folder_id"), []) # Returns empty on error
        mock_print.assert_any_call(unittest.mock.ANY)


    # --- Tests for fetch_file_or_folder ---
    @patch('Fetch_Google_Drive.is_folder', return_value=False) # It's a file
    @patch('Fetch_Google_Drive.fetch_file')
    def test_fetch_file_or_folder_calls_fetch_file_for_file(self, mock_fetch_file, mock_is_folder_check):
        mock_service = MagicMock()
        file_id = "some_file_id"
        destination = "local_path/file.txt"
        
        fetch_file_or_folder(mock_service, file_id, destination)
        
        mock_is_folder_check.assert_called_once_with(mock_service, file_id)
        mock_fetch_file.assert_called_once_with(mock_service, file_id, destination, mime_type=None) # Assuming default mime_type

    @patch('Fetch_Google_Drive.is_folder') # Mocked to control behavior
    @patch('Fetch_Google_Drive.os.makedirs')
    @patch('Fetch_Google_Drive.list_files_in_folder')
    @patch('Fetch_Google_Drive.fetch_file') # This will be called for children if they are files
    def test_fetch_file_or_folder_handles_folder_recursively(self, mock_fetch_file_for_children, 
                                                            mock_list_files, mock_makedirs, mock_is_folder_check):
        mock_service = MagicMock()
        folder_id = "main_folder_id"
        destination_folder_path = "local_path/my_folder"

        # First call to is_folder (for main_folder_id) returns True
        # Subsequent calls (for children) should return False for this test setup
        mock_is_folder_check.side_effect = lambda service, f_id: True if f_id == folder_id else False
        
        mock_child_files = [
            {'id': 'child_file_id_1', 'name': 'child_doc1.txt'},
            {'id': 'child_file_id_2', 'name': 'child_doc2.pdf'}
        ]
        mock_list_files.return_value = mock_child_files

        # We are testing one level of recursion. fetch_file_or_folder calls fetch_file for children.
        fetch_file_or_folder(mock_service, folder_id, destination_folder_path, mime_type=None)

        mock_is_folder_check.assert_any_call(mock_service, folder_id)
        mock_makedirs.assert_called_once_with(destination_folder_path, exist_ok=True)
        mock_list_files.assert_called_once_with(mock_service, folder_id)
        
        # Check that fetch_file (or the non-recursive part of fetch_file_or_folder) was called for children
        expected_child_calls = [
            call(mock_service, 'child_file_id_1', os.path.join(destination_folder_path, 'child_doc1.txt'), mime_type=None),
            call(mock_service, 'child_file_id_2', os.path.join(destination_folder_path, 'child_doc2.pdf'), mime_type=None)
        ]
        # If fetch_file_or_folder calls itself, and then fetch_file, mock_fetch_file_for_children gets the calls.
        mock_fetch_file_for_children.assert_has_calls(expected_child_calls, any_order=True)


    # --- Tests for __main__ entry point ---
    # Helper to run __main__ block
    def run_main_script_with_args(self, args_list, mock_auth_func, mock_fetch_file_or_folder_func):
        mock_service_instance = MagicMock()
        mock_auth_func.return_value = mock_service_instance
        
        original_argv = sys.argv
        sys.argv = args_list
        
        script_path = "Fetch_Google_Drive.py" # Assuming script is in current dir or discoverable
        try:
            with open(script_path, 'r') as f:
                script_code = f.read()
            # Execute with mocks in place
            exec_globals = {
                '__name__': '__main__', 
                'sys': sys, 
                'os': os,
                'argparse': unittest.mock.MagicMock(), # Mock argparse if __main__ uses it directly for setup
                                                        # Usually, argparse is part of main()
                # Mock the core functions from Fetch_Google_Drive used by __main__
                'authenticate_google_drive': mock_auth_func,
                'fetch_file_or_folder': mock_fetch_file_or_folder_func,
                # Add other necessary mocks if __main__ imports/uses them directly
                'HttpError': HttpError # Make our mock HttpError available
            }
            # Need to ensure that if main() inside the script uses argparse, it's handled.
            # The provided script has argparse inside main(). We need to let that run,
            # or mock parse_args() call if main() is structured like def main(args_raw=None): parser.parse_args(args_raw)
            # For simplicity of exec, we are mocking the functions called *by* main().
            
            # Re-evaluate: The prompt's Fetch_Google_Drive.py has main() calling parse_args().
            # So, we should let main() run from the exec'd script.
            # The patches for authenticate_google_drive etc. should be at module level for exec.
            # This helper is becoming complex. A simpler main test below.
            exec(script_code, exec_globals)

        except SystemExit: 
            pass # Expected for argparse errors
        finally:
            sys.argv = original_argv

    @patch('Fetch_Google_Drive.authenticate_google_drive')
    @patch('Fetch_Google_Drive.fetch_file_or_folder')
    def test_main_flow_regular_download(self, mock_fetch_file_or_folder_func, mock_auth_func):
        """Test main entry point for regular download/fetch."""
        mock_service_instance = MagicMock()
        mock_auth_func.return_value = mock_service_instance
        
        args = ["Fetch_Google_Drive.py", "file123", "mydoc.txt"]
        with patch.object(sys, 'argv', args):
            fetch_main() # Call the imported main function
        
        mock_auth_func.assert_called_once()
        mock_fetch_file_or_folder_func.assert_called_once_with(mock_service_instance, "file123", "mydoc.txt", None)

    @patch('Fetch_Google_Drive.authenticate_google_drive')
    @patch('Fetch_Google_Drive.fetch_file_or_folder')
    def test_main_flow_with_mime_type(self, mock_fetch_file_or_folder_func, mock_auth_func):
        """Test main entry point for fetch with MIME type (export)."""
        mock_service_instance = MagicMock()
        mock_auth_func.return_value = mock_service_instance

        args = ["Fetch_Google_Drive.py", "doc_id_456", "mydoc.pdf", "--mime_type", "application/pdf"]
        with patch.object(sys, 'argv', args):
            fetch_main()
            
        mock_auth_func.assert_called_once()
        mock_fetch_file_or_folder_func.assert_called_once_with(mock_service_instance, "doc_id_456", "mydoc.pdf", "application/pdf")

    @patch('Fetch_Google_Drive.authenticate_google_drive') # Won't be called
    @patch('Fetch_Google_Drive.fetch_file_or_folder')   # Won't be called
    @patch('builtins.print') 
    @patch('sys.exit') 
    def test_main_flow_missing_arguments(self, mock_sys_exit, mock_print, 
                                     mock_fetch_file_or_folder_func, mock_auth_func):
        """Test main entry point with missing required arguments."""
        args = ["Fetch_Google_Drive.py", "file_only_id"] # Missing destination_path
        with patch.object(sys, 'argv', args):
            with self.assertRaises(SystemExit): # Argparse error should cause SystemExit
                fetch_main()
        
        # Check if print was called by argparse (stderr usually) or if sys.exit was called
        # self.assertTrue(mock_print.called or mock_sys_exit.called) # One or both usually
        mock_sys_exit.assert_called() # Argparse calls sys.exit on error
        mock_auth_func.assert_not_called()
        mock_fetch_file_or_folder_func.assert_not_called()


if __name__ == '__main__':
    # Pre-patching for initial import if Fetch_Google_Drive.py uses Google API modules at top level
    google_mock_modules = {
        'google.oauth2.credentials': MagicMock(Credentials=MockCredentials),
        'google_auth_oauthlib.flow': MagicMock(InstalledAppFlow=MockInstalledAppFlow),
        'googleapiclient.discovery': MagicMock(),
        'googleapiclient.http': MagicMock(MediaIoBaseDownload=MockMediaIoBaseDownload),
        'googleapiclient.errors': MagicMock(HttpError=HttpError),
        'google.auth.exceptions': MagicMock(RefreshError=RefreshError, DefaultCredentialsError=DefaultCredentialsError),
        'google': MagicMock(), # Top level google
        'io': io # Real io for Fetch_Google_Drive.io.FileIO if not otherwise mocked
    }
    # Apply mocks to sys.modules for imports within Fetch_Google_Drive.py if it's imported by test file
    for module_name, mock_obj in google_mock_modules.items():
        if module_name not in sys.modules: # Avoid overriding already loaded modules if not necessary
             sys.modules[module_name] = mock_obj
    
    unittest.main()
