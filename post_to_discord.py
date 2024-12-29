import requests
import sys
import os

# Function to process message using ChatGPT

def process_message_with_chatgpt(api_key, message):
    if not api_key:
        raise ValueError("ChatGPT API key is not set. Please set the CHATGPT_API_KEY environment variable.")

    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    data = {
        "model": "gpt-3.5-turbo",
        "messages": [
            {"role": "system", "content": "You are a QA engineer reading an automated system status. Give a response to post in a team chat about the status message."},
            {"role": "user", "content": message},
        ],
        "max_tokens": 100,
    }

    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    except requests.exceptions.RequestException as e:
        print(f"Error interacting with ChatGPT: {e}")
        return message  # Fallback to the original message if ChatGPT fails

# Function to post message to Discord
def post_to_discord(bot_token, channel_id, message, image_path=None):
    chatgpt_api_key = os.getenv("CHATGPT_API_KEY")
    if chatgpt_api_key:
        print("Processing message with ChatGPT...")
        message = process_message_with_chatgpt(chatgpt_api_key, message)

    url = f"https://discord.com/api/v10/channels/{channel_id}/messages"
    headers = {
        "Authorization": f"Bot {bot_token}"
    }
    data = {
        "content": message
    }

    files = None
    if image_path:
        if not os.path.isfile(image_path):
            print(f"Error: File '{image_path}' not found.")
            sys.exit(1)
        with open(image_path, "rb") as file:
            files = {"file": file}
            response = requests.post(url, headers=headers, data=data, files=files)
    else:
        response = requests.post(url, headers=headers, data=data)

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
