# Inside api/app.py (or as a separate utility)
import hmac
import hashlib
import json
from urllib.parse import unquote

def verify_telegram_init_data(init_data_raw, bot_token):
    """
    Verifies Telegram initData signature.
    Returns user data dict if valid, else None.
    """
    try:
        # Parse initData
        data = dict(pair.split('=', 1) for pair in unquote(init_data_raw).split('&'))
        hash_value = data.pop('hash')
        
        # Sort and create data string
        data_check_string = '\n'.join(f"{k}={v}" for k, v in sorted(data.items()))
        
        # Compute HMAC-SHA256
        secret_key = hmac.new(bot_token.encode(), 'WebAppData'.encode(), hashlib.sha256).digest()
        computed_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
        
        if computed_hash != hash_value:
            return None
        
        # Extract user data
        user_data = json.loads(data['user'])
        return {
            'user_id': user_data['id'],
            'username': user_data.get('username'),
            'first_name': user_data.get('first_name'),
            'profile_photo': user_data.get('photo_url')
        }
    except Exception:
        return None

  # Inside api/app.py
import asyncio
import random
import time

# Global market state
market_price = 100.0  # Starting price
market_history = [100.0]  # For graph (last 100 points)

async def update_market():
    """Background task to update market price every second."""
    while True:
        # Random walk: base change + volatility (Gaussian noise) + slight upward bias
        change = random.gauss(0, 0.5) + 0.1  # Mean 0.1 for upward trend
        market_price = max(1, market_price + change)  # Prevent negative prices
        market_history.append(market_price)
        if len(market_history) > 100:  # Keep last 100 for graph
            market_history.pop(0)
        await asyncio.sleep(1)

# Start background task (in app startup)

# api/app.py
from quart import Quart, request, jsonify
import asyncio
import os
from mongo import get_or_create_user, add_trade, get_recent_trades, users_collection, trades_collection
from verify_init_data import verify_telegram_init_data  # Assume this is in a separate file or inline

app = Quart(__name__)
BOT_TOKEN = os.getenv("BOT_TOKEN", "8312083760:AAGA8Fu9gTWZIiaxzMXt_lzMkR8rNmZLTCY")

# Global active trades: {user_id: {"direction": str, "amount": float, "start_time": float}}
active_trades = {}

# Middleware to verify initData on every request
@app.before_request
async def verify_auth():
    init_data_raw = request.headers.get('Authorization')  # Pass initData in Authorization header
    if not init_data_raw:
        return jsonify({"error": "Missing initData"}), 401
    user_data = verify_telegram_init_data(init_data_raw, BOT_TOKEN)
    if not user_data:
        return jsonify({"error": "Invalid initData"}), 401
    request.user = user_data  # Attach to request

# GET /api/balance - Get user balance
@app.route('/api/balance', methods=['GET'])
async def get_balance():
    user = await get_or_create_user(**request.user)
    return jsonify({"balance": user["balance"]})

# POST /api/add-balance - Admin endpoint (for testing; add auth in production)
@app.route('/api/add-balance', methods=['POST'])
async def add_balance():
    data = await request.get_json()
    amount = data.get('amount', 0)
    if amount <= 0:
        return jsonify({"error": "Invalid amount"}), 400
    user_id = request.user['user_id']
    await users_collection.update_one({"user_id": user_id}, {"$inc": {"balance": amount}})
    return jsonify({"success": True})

# POST /api/deduct-balance - Deduct balance (for trades)
@app.route('/api/deduct-balance', methods=['POST'])
async def deduct_balance():
    data = await request.get_json()
    amount = data.get('amount', 0)
    if amount <= 0:
        return jsonify({"error": "Invalid amount"}), 400
    user_id = request.user['user_id']
    user = await users_collection.find_one({"user_id": user_id})
    if user["balance"] < amount:
        return jsonify({"error": "Insufficient balance"}), 400
    await users_collection.update_one({"user_id": user_id}, {"$inc": {"balance": -amount}})
    return jsonify({"success": True})

# GET /api/price - Get current market price and history
@app.route('/api/price', methods=['GET'])
async def get_price():
    return jsonify({"price": market_price, "history": market_history})

# POST /api/trade - Place a trade
@app.route('/api/trade', methods=['POST'])
async def place_trade():
    data = await request.get_json()
    amount = data.get('amount', 0)
    direction = data.get('direction')  # "UP" or "DOWN"
    if amount <= 0 or direction not in ["UP", "DOWN"]:
        return jsonify({"error": "Invalid trade"}), 400
    user_id = request.user['user_id']
    if user_id in active_trades:
        return jsonify({"error": "Active trade in progress"}), 400
    user = await get_or_create_user(**request.user)
    if user["balance"] < amount:
        return jsonify({"error": "Insufficient balance"}), 400
    
    # Deduct balance and start trade
    await deduct_balance()  # Reuse logic
    start_price = market_price
    active_trades[user_id] = {"direction": direction, "amount": amount, "start_price": start_price, "start_time": time.time()}
    
    # Schedule resolution after 5 seconds
    asyncio.create_task(resolve_trade(user_id, direction, amount, start_price))
    return jsonify({"success": True})

async def resolve_trade(user_id, direction, amount, start_price):
    await asyncio.sleep(5)
    end_price = market_price
    is_win = (direction == "UP" and end_price > start_price) or (direction == "DOWN" and end_price < start_price)
    profit = amount * 0.95 if is_win else -amount
    await users_collection.update_one({"user_id": user_id}, {"$inc": {"balance": profit}})
    await add_trade(user_id, request.user['username'], amount, direction, "win" if is_win else "loss", profit)
    del active_trades[user_id]

# GET /api/open-trades - Get all active trades
@app.route('/api/open-trades', methods=['GET'])
async def get_open_trades():
    up_trades = [{"username": request.user.get('username', 'Unknown'), "amount": t["amount"]} for t in active_trades.values() if t["direction"] == "UP"]
    down_trades = [{"username": request.user.get('username', 'Unknown'), "amount": t["amount"]} for t in active_trades.values() if t["direction"] == "DOWN"]
    return jsonify({"up": up_trades, "down": down_trades})

# GET /api/history - Get last 15 trades
@app.route('/api/history', methods=['GET'])
async def get_history():
    trades = await get_recent_trades()
    return jsonify(trades)

# Startup: Start market update task
@app.before_serving
async def startup():
    asyncio.create_task(update_market())

if __name__ == '__main__':
    app.run()
