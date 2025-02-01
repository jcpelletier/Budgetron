from __future__ import print_function
import os
import io
import pickle
import argparse
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

# If modifying these SCOPES, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

def authenticate_google_drive():
    """Authenticate with Google Drive and return a service object."""
    creds = None
    if os.path.exists('token.json'):
        try:
            with open('token.json', 'r') as token_file:
                creds = Credentials.from_authorized_user_file('token.json', SCOPES)
        except Exception as e:
            print(f"Error reading token.json: {e}")
            creds = None
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as e:
                print(f"Error refreshing token: {e}")
                creds = None
        if not creds:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=58142)
        with open('token.json', 'w') as token_file:
            token_file.write(creds.to_json())
    return build('drive', 'v3', credentials=creds)

def is_folder(service, file_id):
    """Check if a given file ID corresponds to a folder."""
    try:
        file_metadata = service.files().get(fileId=file_id, fields="mimeType").execute()
        return file_metadata.get("mimeType") == "application/vnd.google-apps.folder"
    except Exception as e:
        print(f"Error checking file type: {e}")
        return False

def list_files_in_folder(service, folder_id):
    """Retrieve a list of all file IDs inside a folder."""
    try:
        query = f"'{folder_id}' in parents and trashed=false"
        results = service.files().list(q=query, fields="files(id, name)").execute()
        return results.get('files', [])
    except Exception as e:
        print(f"Error listing folder contents: {e}")
        return []

def fetch_file(service, file_id, destination_path, mime_type=None):
    """Fetch a file from Google Drive and save it locally."""
    try:
        if mime_type:
            request = service.files().export_media(fileId=file_id, mimeType=mime_type)
        else:
            request = service.files().get_media(fileId=file_id)
        
        with io.FileIO(destination_path, 'wb') as file:
            downloader = MediaIoBaseDownload(file, request)
            done = False
            while not done:
                status, done = downloader.next_chunk()
                print(f"Download progress: {int(status.progress() * 100)}%")
        print(f"File saved to {destination_path}")
    except Exception as e:
        print(f"An error occurred: {e}")

def fetch_file_or_folder(service, file_id, destination_path, mime_type=None):
    """Download a file or a folder from Google Drive."""
    if is_folder(service, file_id):
        os.makedirs(destination_path, exist_ok=True)
        files = list_files_in_folder(service, file_id)
        for file in files:
            file_path = os.path.join(destination_path, file["name"])
            fetch_file_or_folder(service, file["id"], file_path)  # Recursive call
    else:
        fetch_file(service, file_id, destination_path, mime_type)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download files or folders from Google Drive.")
    parser.add_argument("file_id", type=str, help="The ID of the Google Drive file or folder to download.")
    parser.add_argument("destination_path", type=str, help="The local path to save the file or folder.")
    parser.add_argument("--mime_type", type=str, default=None, help="The MIME type to download the file as (e.g., 'text/csv').")

    args = parser.parse_args()

    service = authenticate_google_drive()
    fetch_file_or_folder(service, args.file_id, args.destination_path, args.mime_type)
