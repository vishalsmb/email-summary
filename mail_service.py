from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from fastapi import HTTPException
from datetime import datetime, timedelta
import os
import base64
import time
import mail_details_table as mdt
import summary_service as sum_ser
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s")

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


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


gmail_service = None


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
        logging.error(f"Error parsing email: {str(e)}")

    return None


def get_message_details(id):
    return gmail_service.users().messages().get(userId="me", id=id).execute()


def get_summary(new_message):
    return sum_ser.summarize(new_message['full_msg'])


def format_message(id, message_details):
    subject = next(
        header["value"] for header in message_details["payload"]["headers"] if header["name"] == "Subject")
    sender = next(
        header["value"] for header in message_details["payload"]["headers"] if header["name"] == "From")

    return {
        "id": id,
        "full_msg": '',
        "from": sender,
        "categories": ["inbox"],  # You can customize this based on your criteria
        "labels": message_details["labelIds"],
        "subject": subject,
        "timestamp": datetime.fromtimestamp(int(message_details["internalDate"]) / 1000).strftime(
            "%Y-%m-%d %H:%M:%S"),
    }


# Fetch Gmail messages
def fetch_gmail_messages():
    try:
        global gmail_service
        gmail_service = get_gmail_service()

        # Define the label IDs you want to include
        label_ids_to_include = ["newsletters-ml-ds", "newsletters-ml-ds-alphasignal", "newsletters-productivity", "career-it-technology-linkedin-newsletters"]

        # Build the query to fetch emails from the specified labeled folders
        query = f"after:{(datetime.now() - timedelta(days=1)).strftime('%Y/%m/%d')} label:({' OR '.join(label_ids_to_include)})"

        logging.info(query)

        # Fetch Gmail messages using the Gmail API
        results = gmail_service.users().messages().list(userId="me", q=query).execute()

        messages = results.get("messages", [])

        # Process each message and update mail_data
        for message in messages:
            if not mdt.check_id_exists(message['id']):
                message_details = get_message_details(message['id'])
                new_message = format_message(message['id'], message_details)
                new_message["full_msg"] = get_email_text(message_details)

                new_message["summary"] = get_summary(new_message)
                mdt.insert_record_to_mail_detail(new_message)

                time.sleep(10)

    except HttpError as e:
        raise HTTPException(status_code=e.resp.status, detail=e._get_reason())


def fetch_local_messages():
    return mdt.select_all_records_since_yesterday()
