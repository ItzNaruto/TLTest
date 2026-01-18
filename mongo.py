# mongo.py
import motor.motor_asyncio
import os
from datetime import datetime

# MongoDB connection
MONGODB_URL = os.getenv("MONGODB_URL", "mongodb+srv://Kora:Kora@kora.dcxobo3.mongodb.net/?appName=Kora")
client = motor.motor_asyncio.AsyncIOMotorClient(MONGODB_URL)
db = client["trading_simulator"]

# User schema (stored in 'users' collection)
# Fields: user_id (unique), username, first_name, profile_photo, balance
users_collection = db["users"]

# Trade schema (stored in 'trades' collection)
# Fields: user_id, username, amount, direction ("UP" or "DOWN"), start_time, end_time, result ("win" or "loss"), profit_amount
trades_collection = db["trades"]

# Helper to get or create user
async def get_or_create_user(user_id, username, first_name, profile_photo):
    user = await users_collection.find_one({"user_id": user_id})
    if not user:
        user = {
            "user_id": user_id,
            "username": username,
            "first_name": first_name,
            "profile_photo": profile_photo,
            "balance": 1000  # Starting balance
        }
        await users_collection.insert_one(user)
    return user

# Helper to add trade to history
async def add_trade(user_id, username, amount, direction, result, profit_amount):
    trade = {
        "user_id": user_id,
        "username": username,
        "amount": amount,
        "direction": direction,
        "start_time": datetime.utcnow(),
        "end_time": datetime.utcnow(),  # Will be updated on completion
        "result": result,
        "profit_amount": profit_amount
    }
    await trades_collection.insert_one(trade)

# Helper to get last 15 trades for history
async def get_recent_trades(limit=15):
    cursor = trades_collection.find().sort("start_time", -1).limit(limit)
    return await cursor.to_list(length=limit)
