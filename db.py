from pymongo import MongoClient

from .settings import DB_PORT, DB_HOST

client = MongoClient(DB_HOST, DB_PORT)
db_client = client.Zhihu