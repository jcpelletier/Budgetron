from flask import Flask, request
import sys

app = Flask(__name__)

# Use the link_token from the argument or environment
link_token = None

@app.route("/")
def index():
    if not link_token:
        return "Error: No link token provided. Please restart with a valid link token.", 400

    # Render a simple HTML page with Plaid Link
    return f"""
    <html>
    <head>
        <script src="https://cdn.plaid.com/link/v2/stable/link-initialize.js"></script>
    </head>
    <body>
        <button id="linkButton">Connect a Bank Account</button>
        <script>
            const handler = Plaid.create({{
                token: "{link_token}",
                onSuccess: function(public_token, metadata) {{
                    alert('Public token: ' + public_token);
                }},
                onExit: function(err, metadata) {{
                    if (err) {{
                        console.error('Error:', err);
                    }}
                }}
            }});
            document.getElementById('linkButton').addEventListener('click', function() {{
                handler.open();
            }});
        </script>
    </body>
    </html>
    """

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python app.py <link_token>")
        sys.exit(1)

    # Get the link_token from the command-line argument
    link_token = sys.argv[1]

    # Run the Flask app
    app.run(port=5000)
