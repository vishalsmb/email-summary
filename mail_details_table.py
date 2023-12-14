import logging
import os
from datetime import datetime, timedelta

import re

from db_server import mongo_db_client


def get_db_n_collection(database_name=os.environ["DB_NAME"], collection_name=os.environ["COLLECTION_NAME"]):
    database = mongo_db_client[database_name]
    collection = database[collection_name]
    return database, collection


def insert_record_to_mail_detail(record):
    try:
        not_req_keys = ['full_msg']
        request = {key: value for key, value in record.items() if key not in not_req_keys}
        database, collection = get_db_n_collection()
        # Insert the record into the collection
        result = collection.insert_one(request)
        logging.info(f"Record inserted with ID: {result.inserted_id}")
    except Exception as e:
        logging.error(f"Error inserting record: {e}")


# insert_record_to_mail_detail("MailSummary", "MailDetails", sample_record)


def find_ids_only(database_name, collection_name):
    try:
        database, collection = get_db_n_collection()
        # Query the collection and project only the "id" field
        result = collection.find({}, {"_id": 0, "id": 1})
        return result
    except Exception as e:
        logging.error(f"Error querying ids: {e}")
        return None


# find_ids_only("MailSummary", "MailDetails")


def check_id_exists(record_id):
    try:
        database, collection = get_db_n_collection()
        # Query the collection by ID
        result = collection.find_one({"id": record_id})
        return result is not None
    except Exception as e:
        logging.error(f"Error checking ID existence: {e}")
        return False


def select_all_records_since_yesterday():
    try:
        database, collection = get_db_n_collection()
        result = collection.find({
            "timestamp": {"$gte": datetime.now() - timedelta(days=1)}
        })

        return [r for r in result]
    except Exception as e:
        logging.error(f"Error Querying records: {e}")
        return None


def fetch_paginated_records(request, page, per_page, mail_id, date, search):
    try:
        database, collection = get_db_n_collection()
        skip = (page - 1) * per_page

        # Construct the query based on the provided filters
        query = {}
        if mail_id:
            query["from"] = {"$regex": re.compile(".*" + mail_id + ".*", re.IGNORECASE)}
        if date:
            date_obj = datetime.strptime(date, "%Y-%m-%d")
            query["timestamp"] = {"$gte": date_obj, "$lt": date_obj + timedelta(days=1)}
        if search:
            query["summary"] = {"$regex": re.compile(".*" + search + ".*", re.IGNORECASE)}

        mails = collection.find(query).skip(skip).limit(per_page)
        total_items = collection.count_documents(query)
        return {
            "request": request,
            "mails": mails,
            "page": page,
            "per_page": per_page,
            "total_items": total_items,
        }
    except Exception as e:
        logging.error(f"Error Querying records: {e}")
        return None
