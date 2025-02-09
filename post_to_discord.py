import requests
import sys
import os

# Configure UTF-8 encoding to avoid UnicodeEncodeError
sys.stdout.reconfigure(encoding='utf-8')

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
            {"role": "system",
             "content": "You are a financial assistance bot reading an automated system status. Write a brief update for the solo developer to post in an update chat about the status message. Do not suggest you are fixing anything. Use a red emoticon if it is something bad. Use a green emoticon if it is something good."},
            {"role": "user", "content": message},
        ],
        "max_tokens": 100,
    }

    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    except requests.exceptions.HTTPError as e:
        print(f"HTTP error interacting with ChatGPT: {e}")
    except requests.exceptions.RequestException as e:
        print(f"Request error interacting with ChatGPT: {e}")

    return message  # Fallback to the original message if ChatGPT fails

# Function to post message to Discord
def post_to_discord(bot_token, channel_id, message, use_chatgpt=False, image_path=None):
    """Posts a message to Discord, optionally processing it with ChatGPT first."""
    if use_chatgpt:
        chatgpt_api_key = os.getenv("CHATGPT_API_KEY")
        if not chatgpt_api_key:
            print("Error: ChatGPT API key is not set. Please set the CHATGPT_API_KEY environment variable.")
            sys.exit(1)

        print("Processing message with ChatGPT...")
        message = process_message_with_chatgpt(chatgpt_api_key, message)

    url = f"https://discord.com/api/v10/channels/{channel_id}/messages"
    headers = {
        "Authorization": f"Bot {bot_token}",
        "Content-Type": "application/json",
    }
    data = {"content": message}

    try:
        if image_path:
            if not os.path.isfile(image_path):
                print(f"Error: File '{image_path}' not found.")
                sys.exit(1)
            with open(image_path, "rb") as file:
                files = {"file": file}
                response = requests.post(url, headers=headers, data=data, files=files)
        else:
            response = requests.post(url, headers=headers, json=data)

        response.raise_for_status()
        print("✅ Message sent successfully to Discord!")
    except requests.exceptions.HTTPError as http_err:
        print(f"❌ HTTP error: {http_err}")
        print(f"Response text: {response.text}")  # Log response for debugging
    except requests.exceptions.RequestException as req_err:
        print(f"❌ Request error: {req_err}")

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: python post_to_discord.py <bot_token> <channel_id> <message> [--use_chatgpt] [<image_path>]")
        sys.exit(1)

    bot_token = sys.argv[1]
    channel_id = sys.argv[2]
    message = sys.argv[3]

    # Check for optional arguments
    use_chatgpt = "--use_chatgpt" in sys.argv
    image_path = None
    if len(sys.argv) > 4:
        last_arg = sys.argv[-1]
        if last_arg != "--use_chatgpt":
            image_path = last_arg

    post_to_discord(bot_token, channel_id, message, use_chatgpt, image_path)
