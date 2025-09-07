# slack.py

from fastapi import Request
import json
import secrets
import base64
import asyncio
import httpx

from fastapi.responses import HTMLResponse

from integrations.integration_item import IntegrationItem
from redis_client import add_key_value_redis, get_value_redis, delete_key_redis

#app's credentials and config used to create and complete aouth flow with hubspot
CLIENT_ID = '7ce948f5-b4c8-41fd-9809-4ccf5670a3e7'
CLIENT_SECRET = 'abb867e1-9975-472e-a6a9-9d1c58d9b49e'
REDIRECT_URI = 'http://localhost:8000/integrations/hubspot/oauth2callback'
SCOPE = 'oauth crm.objects.contacts.read'


async def authorize_hubspot(user_id, org_id):
    # Generate a secure random string
    state = secrets.token_urlsafe(32)

    # Save user info in Redis using the state as the key
    state_data = {
        "user_id": user_id,
        "org_id": org_id
    }
    await add_key_value_redis(f"hubspot_state:{state}", json.dumps(state_data), expire=600)

    # Optional: You can also encode the state if you want, but not required


    # Build the HubSpot authorization URL
    auth_url = (
        f"https://app.hubspot.com/oauth/authorize"
        f"?client_id={CLIENT_ID}"
        f"&redirect_uri={REDIRECT_URI}"
        f"&scope={SCOPE}"
        f"&state={state}"  # Use plain `state`, not encoded
        f"&response_type=code"
    )

    return auth_url

async def oauth2callback_hubspot(request: Request):
    if request.query_params.get("error"):
        raise HTTPException(status_code=400, detail=request.query_params.get("error_description"))

    code = request.query_params.get("code")
    state = request.query_params.get("state")

    if not state:
        return {"error": "Missing state"}

    saved_state_json = await get_value_redis(f"hubspot_state:{state}")
    if not saved_state_json:
        return {"error": "Invalid state parameter"}

    state_data = json.loads(saved_state_json)
    user_id = state_data.get("user_id")
    org_id = state_data.get("org_id")

    if not user_id or not org_id:
        return {"error": "Missing user/org from state"}

    async with httpx.AsyncClient() as client:
        token_response = await client.post(
            "https://api.hubapi.com/oauth/v1/token",
            data={
                "grant_type": "authorization_code",
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "redirect_uri": REDIRECT_URI,
                "code": code,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

    await asyncio.gather(
        delete_key_redis(f"hubspot_state:{state}"),
        add_key_value_redis(f"hubspot_credentials:{org_id}:{user_id}", json.dumps(token_response.json()), expire=600)
    )

    return HTMLResponse(content="""
    <html>
      <h1> HubSpot Auth Complete!</h1>
      <p>You can close this window now.</p>
    </html>
    """)

async def get_hubspot_credentials(user_id, org_id):
    key = f"hubspot_credentials:{org_id}:{user_id}" #Constructs the Redis key used to store credentials.
    credentials_json = await get_value_redis(key)#fetches the value stored in Redis for that key

    if not credentials_json:
        return {"error": "No credentials found. Please reauthorize."}#If Redis has nothing stored for that key, it returns an error message

#If credentials were found, it tries to decode the JSON string into a Python dictionary (json.loads).
# If successful, it returns the dictionary — which should contain access_token, refresh_token
    try:
        credentials = json.loads(credentials_json)
        return credentials
    except json.JSONDecodeError:
        return {"error": "Failed to parse credentials"} #except block catches coding error and returns message if if JSON string is invalid

async def create_integration_item_metadata_object(response_json):
    items = []

    for result in response_json.get("results", []):
        contact_id = result.get("id")
        props = result.get("properties", {})

        # Build full name
        firstname = props.get("firstname", "")
        lastname = props.get("lastname", "")
        name = f"{firstname} {lastname}".strip() or "Unnamed Contact"

        # Parse optional timestamps
        created = props.get("createdate")
        last_modified = props.get("lastmodifieddate")

        try:
            creation_time = datetime.fromisoformat(created[:-1]) if created else None
        except Exception:
            creation_time = None

        try:
            last_modified_time = datetime.fromisoformat(last_modified[:-1]) if last_modified else None
        except Exception:
            last_modified_time = None

        # Construct contact profile URL (not clickable but useful)
        url = f"https://app.hubspot.com/contacts/{contact_id}" if contact_id else None

        item = IntegrationItem(
            id=contact_id,
            name=name,
            creation_time=creation_time,
            last_modified_time=last_modified_time,
            url=url,
            visibility=True
        )

        items.append(item)

    return items

async def get_items_hubspot(credentials):
    access_token = credentials.get("access_token")
    if not access_token:
        return {"error": "Missing access token"}

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://api.hubapi.com/crm/v3/objects/contacts",
            headers=headers
        )

    if response.status_code != 200:
        return {
            "error": "Failed to fetch contacts",
            "status_code": response.status_code,
            "details": response.text
        }

    data = response.json()
    items = []

    for contact in data.get("results", []):
        props = contact.get("properties", {})
        name = f"{props.get('firstname', '')} {props.get('lastname', '')}".strip()
        item = IntegrationItem(
            id=contact.get("id"),
            name=name,
            creation_time=props.get("createdate"),
            last_modified_time=props.get("lastmodifieddate"),
            url=f"https://app.hubspot.com/contacts/{contact.get('id')}",
            visibility=True
        )
        items.append(item)

    # Optional: print to console
    print("Final Integration Items:")
    for item in items:
        print(item.__dict__)

    return items