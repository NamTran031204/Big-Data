from pymongo import MongoClient

# Kết nối
client = MongoClient("mongodb+srv://admin123:admin111111@bigdata.rsbygb5.mongodb.net/?appName=BigData")
db = client["testdb"]
collection = db["users"]

# CREATE
user = {"name": "Huy", "age": 21}
collection.insert_one(user)

# READ
print("All users:")
for u in collection.find():
    print(u)

# # UPDATE
# collection.update_one({"name": "Huy"}, {"$set": {"age": 22}})

# # DELETE
# collection.delete_one({"name": "Huy"})

print("Done!")