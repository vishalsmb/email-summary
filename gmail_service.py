from fastapi import BackgroundTasks, Depends
from fastapi.templating import Jinja2Templates
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from fastapi import HTTPException
from datetime import datetime, timedelta
import os
import base64
import quopri  # For decoding quoted-printable content
from html import escape
from bs4 import BeautifulSoup  # You may need to install the BeautifulSoup library

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


def decode_part(part):
    """Decode a part based on its encoding."""
    body = part['body']
    if 'data' in body:
        # The content is base64 encoded
        data = base64.urlsafe_b64decode(body['data']).decode('utf-8')
    elif 'attachmentId' in body:
        # Handle attachments if needed
        data = 'Attachment: (use Gmail API to download)'
    else:
        # Handle other cases as needed
        data = ''

    # Decode based on Content-Transfer-Encoding
    encoding = body.get('attachmentId', 'none')
    if encoding == 'quoted-printable':
        data = quopri.decodestring(data).decode('utf-8')
    elif encoding == 'base64':
        data = base64.b64decode(data).decode('utf-8')

    return data


def render_part(part):
    """Render a part based on its MIME type."""
    mimeType = part.get('mimeType', 'text/plain')
    if mimeType == 'text/plain':
        return escape(decode_part(part))
    elif mimeType == 'text/html':
        # If the part is HTML, you can further process it (e.g., remove inline images)
        # before rendering. Here, we use BeautifulSoup for simplicity.
        html_content = decode_part(part)
        soup = BeautifulSoup(html_content, 'html.parser')
        return soup.prettify()  # You can modify this based on your requirements
    else:
        return ''  # Handle other MIME types as needed


def get_gmail_service():
    credentials = None
    if os.path.exists("token.json"):
        credentials = Credentials.from_authorized_user_file("token.json")
    if not credentials or not credentials.valid:
        if credentials and credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            credentials = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open("token.json", "w") as token:
            token.write(credentials.to_json())

    service = build("gmail", "v1", credentials=credentials)
    return service


gmail_service = get_gmail_service()


def get_email_text(message):
    try:
        payload = message['payload']

        try:
            #  check if it has a body
            if 'body' in payload:
                data = payload['body']['data']
                # Decode the base64-encoded data and return the text
                return base64.urlsafe_b64decode(data).decode('utf-8')
        except:
            pass

        parts = payload['parts']

        # Check if the message is multipart (contains multiple parts)
        if parts:
            # Iterate through the parts to find the text/plain part
            for part in parts:
                if 'body' in part:
                    data = part['body']['data']
                    # Decode the base64-encoded data and return the text
                    return base64.urlsafe_b64decode(data).decode('utf-8')

    except Exception as e:
        print(f"Error parsing email: {str(e)}")

    return None


# Fetch Gmail messages
def fetch_gmail_messages():
    try:
        mail_data = {
            "mails": []
        }
        global gmail_service

        # Define the label IDs you want to include
        label_ids_to_include = ["NewsLetters", "Inbox"]

        # Build the query to fetch emails from the specified labeled folders
        query = f"after:{(datetime.now() - timedelta(days=1)).strftime('%Y/%m/%d')} label:({' OR '.join(label_ids_to_include)})"

        # Fetch Gmail messages using the Gmail API
        results = gmail_service.users().messages().list(userId="me", q=query).execute()

        messages = results.get("messages", [])

        # Process each message and update mail_data
        for message in messages:
            message_details = gmail_service.users().messages().get(userId="me", id=message["id"]).execute()
            subject = next(
                header["value"] for header in message_details["payload"]["headers"] if header["name"] == "Subject")
            sender = next(
                header["value"] for header in message_details["payload"]["headers"] if header["name"] == "From")

            text = get_email_text(message_details)

            new_message = {
                "id": message["id"],
                "full_msg": text,
                "from": sender,
                "categories": ["inbox"],  # You can customize this based on your criteria
                "labels": message_details["labelIds"],
                "subject": subject,
                "timestamp": datetime.fromtimestamp(int(message_details["internalDate"]) / 1000).strftime(
                    "%Y-%m-%d %H:%M:%S"),
            }

            mail_data["mails"].append(new_message)
        return mail_data
    except HttpError as e:
        raise HTTPException(status_code=e.resp.status, detail=e._get_reason())
