from pymongo import MongoClient, UpdateOne
from pymongo.errors import BulkWriteError
from typing import List, Dict, Any, Optional
import logging


class MongoConnector:
    """
    MongoDB Atlas Connector with:
    - Connection manager
    - CRUD wrappers
    - Bulk insert optimization
    - Upsert logic
    """

    def __init__(self, uri: str, db_name: str):
        self.uri = uri
        self.db_name = db_name
        self.client: Optional[MongoClient] = None
        self.db = None

    # ======================
    # Connection Management
    # ======================
    def connect(self):
        try:
            self.client = MongoClient(self.uri)
            self.db = self.client[self.db_name]
            logging.info("Connected to MongoDB Atlas")
        except Exception as e:
            logging.error(f"Connection failed: {e}")
            raise

    def close(self):
        if self.client:
            self.client.close()
            logging.info("Connection closed")

    def get_collection(self, collection_name: str):
        if self.db is None:
            raise Exception("Database not connected")
        return self.db[collection_name]

    # ======================
    # CRUD OPERATIONS
    # ======================
    def insert_one(self, collection_name: str, document: Dict):
        col = self.get_collection(collection_name)
        return col.insert_one(document).inserted_id

    def insert_many(self, collection_name: str, documents: List[Dict]):
        col = self.get_collection(collection_name)
        return col.insert_many(documents).inserted_ids

    def find_one(self, collection_name: str, query: Dict):
        col = self.get_collection(collection_name)
        return col.find_one(query)

    def find_many(self, collection_name: str, query: Dict, limit: int = 0):
        col = self.get_collection(collection_name)
        cursor = col.find(query)
        if limit > 0:
            cursor = cursor.limit(limit)
        return list(cursor)

    def update_one(self, collection_name: str, query: Dict, update: Dict):
        col = self.get_collection(collection_name)
        return col.update_one(query, {'$set': update})

    def update_many(self, collection_name: str, query: Dict, update: Dict):
        col = self.get_collection(collection_name)
        return col.update_many(query, {'$set': update})

    def delete_one(self, collection_name: str, query: Dict):
        col = self.get_collection(collection_name)
        return col.delete_one(query)

    def delete_many(self, collection_name: str, query: Dict):
        col = self.get_collection(collection_name)
        return col.delete_many(query)

    # ======================
    # BULK INSERT OPTIMIZATION
    # ======================
    def bulk_insert(self, collection_name: str, documents: List[Dict], batch_size: int = 5):
        col = self.get_collection(collection_name)
        total_inserted = 0

        for i in range(0, len(documents), batch_size):
            batch = documents[i:i + batch_size]
            try:
                result = col.insert_many(batch, ordered=False)
                total_inserted += len(result.inserted_ids)
            except BulkWriteError as bwe:
                logging.warning(f"Bulk insert error: {bwe.details}")

        return total_inserted

    # ======================
    # UPSERT LOGIC
    # ======================
    def upsert_one(self, collection_name: str, query: Dict, data: Dict):
        col = self.get_collection(collection_name)
        return col.update_one(query, {'$set': data}, upsert=True)

    def bulk_upsert(self, collection_name: str, data_list: List[Dict], key_fields: List[str]):
        """
        key_fields: fields used to identify unique document (like primary key)
        """
        col = self.get_collection(collection_name)
        operations = []

        for data in data_list:
            query = {k: data[k] for k in key_fields if k in data}
            operations.append(
                UpdateOne(query, {'$set': data}, upsert=True)
            )

        if not operations:
            return None

        try:
            result = col.bulk_write(operations, ordered=False)
            return result.bulk_api_result
        except BulkWriteError as bwe:
            logging.error(f"Bulk upsert error: {bwe.details}")
            return None


# ======================
# USAGE EXAMPLE
# ======================
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    MONGO_URI = "mongodb+srv://dungquennua:huycoi234@bigdata.rsbygb5.mongodb.net/?appName=BigData"
    DB_NAME = "users"

    mongo = MongoConnector(MONGO_URI, DB_NAME)
    mongo.connect()

    # Insert example
    mongo.insert_one("testdb", {"name": "Alice", "age": 25})

    # Bulk insert
    docs = [{"name": f"User{i}", "age": i} for i in range(10000)]
    mongo.bulk_insert("testdb", docs, batch_size=5)

    # Upsert example
    mongo.upsert_one("testdb", {"name": "Alice"}, {"age": 30})

    # Bulk upsert
    mongo.bulk_upsert("testdb", docs, key_fields=["name"])

    mongo.close()
