import os
import glob
import subprocess
from datetime import datetime, timedelta
import argparse


def find_latest_csv(folder_path, required_month, required_year):
    """Finds the latest CSV file for the required month and year."""
    try:
        files = glob.glob(os.path.join(folder_path, "*.csv"))
        if not files:
            return None

        for file in files:
            filename = os.path.basename(file)
            try:
                # Extract the "Month YYYY" part of the filename (e.g., "December 2024")
                date_part = filename.split(" -")[0]  # Everything before " - transactions"
                file_date = datetime.strptime(date_part, "%B %Y")
                if file_date.month == required_month and file_date.year == required_year:
                    return file
            except ValueError:
                continue  # Skip files that don't match the expected format

        return None  # If no matching file is found
    except Exception as e:
        print(f"Error finding the latest file: {e}")
        return None


def send_discord_notification(bot_token, channel_id, message, image_path=None, use_chatgpt=True):
    """Calls the post_to_discord.py script to send a notification."""
    command = ["python", "post_to_discord.py", bot_token, channel_id, message]
    if use_chatgpt:
        command.append("--use_chatgpt")
    if image_path:
        command.append(image_path)

    try:
        subprocess.run(command, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Failed to send Discord notification: {e}")


def main():
    parser = argparse.ArgumentParser(description="Driver script for analysis and notifications.")

    # Arguments for file paths and folder locations
    parser.add_argument("--folder", required=True, help="Folder containing the CSV files.")
    parser.add_argument("--classification_csv", required=True, help="CSV file for spending classifications.")

    # Budget and other parameters
    parser.add_argument("--budget", type=float, required=True, help="Target budget for spending analysis.")

    # Discord notification parameters
    parser.add_argument("--bot_token", required=True, help="Discord bot token for notifications.")
    parser.add_argument("--channel_id", required=True, help="Discord channel ID for notifications.")

    args = parser.parse_args()

    # Determine the required month and year (last month)
    today = datetime.now()
    first_of_this_month = today.replace(day=1)
    last_month = first_of_this_month - timedelta(days=1)
    required_month = last_month.month
    required_year = last_month.year

    # Find the CSV file for last month
    latest_file = find_latest_csv(args.folder, required_month, required_year)

    if not latest_file:
        message = "❌ Last month's CSV Export is missing."
        send_discord_notification(args.bot_token, args.channel_id, message)
        print(message)
        return

    print(f"✅ Latest file: {latest_file}")

    # Get absolute paths for scripts
    script_dir = os.path.dirname(os.path.abspath(__file__))
    graph_script = os.path.join(script_dir, "graph_spending.py")
    categories_script = os.path.join(script_dir, "spending_categories.py")

    # Check if scripts exist
    if not os.path.exists(graph_script):
        print("Error: graph_spending.py not found!")
        return
    if not os.path.exists(categories_script):
        print("Error: spending_categories.py not found!")
        return

    # Output file paths
    output_graph = os.path.join(os.getcwd(), "spending_graph.png")
    output_categories = os.path.join(os.getcwd(), "spending_categories.png")

    try:
        # Call the first script (spending graph)
        subprocess.run(["python", graph_script, latest_file, str(args.budget), output_graph], check=True)

        # Call the second script (spending categories)
        subprocess.run(["python", categories_script, latest_file, args.classification_csv, output_categories], check=True)

        # Notify on Discord
        message = (
            f"📊 Analysis completed for file: {latest_file}\n"
            f"Graphs and category breakdowns are ready!"
        )
        send_discord_notification(args.bot_token, args.channel_id, message, image_path=output_graph)
        send_discord_notification(args.bot_token, args.channel_id, "📂 Categories Breakdown", image_path=output_categories)

    except subprocess.CalledProcessError as e:
        error_message = f"❌ An error occurred during processing: {e}"
        send_discord_notification(args.bot_token, args.channel_id, error_message)
        print(error_message)


if __name__ == "__main__":
    main()
