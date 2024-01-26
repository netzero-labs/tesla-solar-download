#!/bin/bash

# Helper script to use with Tesla Fleet API tokens.
# To download tokens, you can use the Netzero Web App:
# https://app.netzeroapp.io
# (See Developer Access in the user menu.)
#
# To refresh tokens, run fleet-api.sh --refresh
#
# Tesla Fleet API documentation: https://developer.tesla.com/docs/fleet-api
# Requires the jq tool: https://jqlang.github.io/jq/download/

set -e

TESLA_API_TOKEN_FILE="tesla-fleet-api-tokens.json"

if [ ! -f $TESLA_API_TOKEN_FILE ]; then
    echo "Token file $TESLA_API_TOKEN_FILE missing"
    exit 1
fi

CURL_CMD="curl -s --tlsv1.2 --tls-max 1.2"

if [ "$1" == "--refresh" ]; then
    # Refresh tokens.
    NETZERO_CLIENT_ID="b7579e1434fe-4e23-aaee-faa4bcdc90d0"
    TESLA_API_REFRESH_TOKEN=$(jq -r .refresh_token $TESLA_API_TOKEN_FILE)

    $CURL_CMD -X POST -H 'Content-Type: application/x-www-form-urlencoded' --data-urlencode 'grant_type=refresh_token' \
        --data-urlencode "client_id=$NETZERO_CLIENT_ID" \
        --data-urlencode "refresh_token=$TESLA_API_REFRESH_TOKEN" \
        https://auth.tesla.com/oauth2/v3/token | jq . > $TESLA_API_TOKEN_FILE
    exit 0
fi

# Extract the access token.
TESLA_API_TOKEN=$(jq -r .access_token $TESLA_API_TOKEN_FILE)

# Get the correct region for your site.
TESLA_BASE_URL=$($CURL_CMD -H "Authorization: Bearer $TESLA_API_TOKEN" https://fleet-api.prd.na.vn.cloud.tesla.com/api/1/users/region | jq -r .response.fleet_api_base_url)
echo "Tesla base url: $TESLA_BASE_URL"

# Get the energy site id.
TESLA_SITE_ID=$($CURL_CMD -H "Authorization: Bearer $TESLA_API_TOKEN" $TESLA_BASE_URL/api/1/products | jq .response[].energy_site_id | grep -v null | head -n1)
echo "Tesla energy site id: $TESLA_SITE_ID"

# Get site info.
$CURL_CMD -H "Authorization: Bearer $TESLA_API_TOKEN" $TESLA_BASE_URL/api/1/energy_sites/$TESLA_SITE_ID/site_info | jq

# To set backup reserve to 50%:
#$CURL_CMD -H "X-Tesla-User-Agent: TeslaApp/4.29.0" -H "Authorization: Bearer $TESLA_API_TOKEN" --json '{"backup_reserve_percent": 50}' $TESLA_BASE_URL/api/1/energy_sites/$TESLA_SITE_ID/backup
