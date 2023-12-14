import os

from pymongo import MongoClient


# MongoDB connection settings
mongo_uri = (f'mongodb+srv://{os.environ["MONGO_DB_USER_NAME"]}'
             f':{os.environ["MONGO_DB_PASSWORD"]}@{os.environ["MONGO_DBCONNECTION_URL"]}/?retryWrites=true&w=majority')

def connect_to_mongodb():
    try:
        # Connect to MongoDB
        client = MongoClient(mongo_uri)
        return client
    except Exception as e:
        print(f"Error connecting to MongoDB: {e}")
        return None

mongo_db_client = connect_to_mongodb()