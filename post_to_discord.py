import requests
import sys
import os

def post_to_discord(bot_token, channel_id, message, image_path=None):
    """
    Posts a message (and optionally an image) to a Discord channel.

    :param bot_token: The bot token for authentication.
    :param channel_id: The ID of the Discord channel to post to.
    :param message: The message content.
    :param image_path: Optional path to an image file.
    """
    url = f"https://discord.com/api/v10/channels/{channel_id}/messages"

    # Headers with bot token
    headers = {
        "Authorization": f"Bot {bot_token}"
    }

    # Prepare data
    data = {
        "content": message
    }

    # If an image path is provided, include it as a file
    files = None
    if image_path:
        if not os.path.isfile(image_path):
            print(f"Error: File '{image_path}' not found.")
            sys.exit(1)
        with open(image_path, "rb") as file:
            files = {"file": file}
            response = requests.post(url, headers=headers, data=data, files=files)
    else:
        # No image, send the message without files
        response = requests.post(url, headers=headers, data=data)

    # Handle response
    try:
        response.raise_for_status()
        print("Message sent successfully!")
    except requests.exceptions.HTTPError as http_err:
        if response.status_code == 401:
            print("Unauthorized: Check your bot token.")
        elif response.status_code == 403:
            print("Forbidden: Ensure the bot has permission to post in this channel.")
        elif response.status_code == 404:
            print("Not Found: Verify the channel ID.")
        else:
            print(f"HTTP error occurred: {http_err}")
    except requests.exceptions.RequestException as req_err:
        print(f"Request error occurred: {req_err}")


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: python post_to_discord.py <bot_token> <channel_id> <message> [<image_path>]")
        print("Example: python post_to_discord.py BOT_TOKEN 123456789012345678 'Hello, Discord!' myimage.png")
        sys.exit(1)

    bot_token = sys.argv[1]
    channel_id = sys.argv[2]
    message = sys.argv[3]
    image_path = sys.argv[4] if len(sys.argv) > 4 else None

    post_to_discord(bot_token, channel_id, message, image_path)
