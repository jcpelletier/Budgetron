import os
import glob
import subprocess
from datetime import datetime
import argparse


def find_csv_for_current_month(folder_path):
    """Checks for a CSV file for the current month and year."""
    try:
        # Get current month and year
        now = datetime.now()
        current_month = now.strftime("%B")  # e.g., "December"
        current_year = now.strftime("%Y")  # e.g., "2024"

        # Construct expected file pattern
        expected_pattern = f"{current_month} {current_year} -*.csv"  # Matches "Month Year -*.csv"
        files = glob.glob(os.path.join(folder_path, expected_pattern))

        return bool(files), current_month, current_year
    except Exception as e:
        print(f"Error while searching for CSV file: {e}")
        return False, None, None


def send_discord_notification(bot_token, channel_id, message):
    """Sends a Discord notification via the post_to_discord.py script."""
    command = ["python", "post_to_discord.py", bot_token, channel_id, message]
    try:
        subprocess.run(command, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Failed to send Discord notification: {e}")


def main():
    parser = argparse.ArgumentParser(description="Check for CSV file for the current month and year.")
    parser.add_argument("--folder", required=True, help="Folder containing the CSV files.")
    parser.add_argument("--bot_token", required=True, help="Discord bot token for notifications.")
    parser.add_argument("--channel_id", required=True, help="Discord channel ID for notifications.")

    args = parser.parse_args()

    # Check for the CSV file for the current month and year
    found, month, year = find_csv_for_current_month(args.folder)

    if found:
        message = f"The CSV file for month: {month} and year: {year} was found."
    else:
        message = f"The CSV file for month: {month} and year: {year} was not found."

    # Send Discord notification
    send_discord_notification(args.bot_token, args.channel_id, message)
    print(message)


if __name__ == "__main__":
    main()
