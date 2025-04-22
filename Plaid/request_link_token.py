from plaid.model.link_token_create_request import LinkTokenCreateRequest
from plaid.model.link_token_create_request_user import LinkTokenCreateRequestUser
from plaid.model.country_code import CountryCode
from plaid.model.products import Products
from plaid.api import plaid_api
from plaid.configuration import Configuration
from plaid.api_client import ApiClient
import sys

# Function to create a Link Token
def create_link_token(client_id, secret, user_id):
    try:
        # Configure the Plaid API
        configuration = Configuration(
            host="https://production.plaid.com",
            api_key={
                'clientId': client_id,
                'secret': secret
            }
        )
        api_client = ApiClient(configuration)
        client = plaid_api.PlaidApi(api_client)

        # Create a Link Token request
        request = LinkTokenCreateRequest(
            products=[Products('transactions')],  # Use the Products enum
            client_name="Internal Project",
            country_codes=[CountryCode('US')],  # Use the CountryCode enum
            language='en',
            user=LinkTokenCreateRequestUser(client_user_id=user_id)
        )

        # Send the request to Plaid
        response = client.link_token_create(request)
        print(f"Link token: {response.link_token}")
        return response.link_token

    except Exception as e:
        print(f"Error creating link token: {e}")
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python request_link_token.py <client_id> <secret> <user_id>")
        sys.exit(1)

    client_id = sys.argv[1]
    secret = sys.argv[2]
    user_id = sys.argv[3]

    create_link_token(client_id, secret, user_id)
