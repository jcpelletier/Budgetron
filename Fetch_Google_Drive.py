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
    # The token.json file stores the user's access and refresh tokens.
    if os.path.exists('token.json'):
        try:
            with open('token.json', 'r') as token_file:
                creds = Credentials.from_authorized_user_file('token.json', SCOPES)
        except Exception as e:
            print(f"Error reading token.json: {e}")
            creds = None
    # If there are no valid credentials, prompt the user to log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as e:
                print(f"Error refreshing token: {e}")
                creds = None
        if not creds:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=58142)
        # Save the credentials for future use as a JSON file
        with open('token.json', 'w') as token_file:
            token_file.write(creds.to_json())
    return build('drive', 'v3', credentials=creds)

def fetch_file(file_id, destination_path, mime_type):
    """Fetch a file from Google Drive and save it locally."""
    service = authenticate_google_drive()
    try:
        if mime_type:
            # Request export for specific MIME type
            request = service.files().export_media(fileId=file_id, mimeType=mime_type)
        else:
            # Request the file in its original format
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

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download files from Google Drive.")
    parser.add_argument("file_id", type=str, help="The ID of the Google Drive file to download.")
    parser.add_argument("destination_path", type=str, help="The local path to save the file.")
    parser.add_argument("--mime_type", type=str, default=None, help="The MIME type to download the file as (e.g., 'text/csv').")

    args = parser.parse_args()

    try:
        fetch_file(args.file_id, args.destination_path, args.mime_type)
    except Exception as e:
        print(f"Critical error: {e}")
