from plaid.configuration import Configuration
from plaid.api_client import ApiClient
from plaid.api import plaid_api
from plaid.model.item_public_token_exchange_request import ItemPublicTokenExchangeRequest
import sys


def get_access_token(client_id, secret, public_token):
    """Exchange a public token for an access token."""
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

        # Exchange public token for access token
        exchange_request = ItemPublicTokenExchangeRequest(public_token=public_token)
        exchange_response = client.item_public_token_exchange(exchange_request)

        access_token = exchange_response.access_token
        print(f"Access token: {access_token}")
        return access_token

    except Exception as e:
        print(f"Error exchanging public token: {e}")
        sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python get_access_token.py <client_id> <secret> <public_token>")
        sys.exit(1)

    client_id = sys.argv[1]
    secret = sys.argv[2]
    public_token = sys.argv[3]

    get_access_token(client_id, secret, public_token)
