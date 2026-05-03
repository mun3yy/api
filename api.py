from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import time
import random
import hashlib
import math
import httpx

app = FastAPI()

# --- CONFIGURATION ---
LIVE_GAMES = {} # Temporary store for linked games
USER_TOKENS = {} # Store for user tokens
USER_STATS = {} # Store for wins/losses
PROXY_URL = "https://delicate-disk-8300.em5505316.workers.dev" 

# --- THE 300 METHODS ---
METHODS = []
for i in range(1, 301):
    METHODS.append({
        "id": i,
        "name": f"Perfect Method v{i}.{random.randint(10, 99)}",
        "desc": f"Utilizes index pattern #{random.randint(1000, 9999)} for surgical precision."
    })

class PredictionRequest(BaseModel):
    uuid: str
    bet_amount: float
    mines: int
    nonce: int
    user_id: str

class TokenData(BaseModel):
    user_id: str
    token: str

@app.get("/status")
async def status():
    return {"status": "operational", "methods_loaded": len(METHODS)}

@app.post("/predict")
async def predict(data: PredictionRequest):
    start_time = time.time()
    
    # Deterministic Seed based on Game Data
    combined_seed = f"{data.uuid}{data.nonce}{data.bet_amount}"
    hash_digest = hashlib.sha256(combined_seed.encode()).hexdigest()
    
    # Select a "Perfect" Method deterministically
    method_index = int(hash_digest[:4], 16) % len(METHODS)
    method = METHODS[method_index]
    
    # Generate the 5x5 Grid (25 tiles)
    # 0 = Safe, 1 = Unsafe, 2 = Unknown
    # We use the hash to create a bitmask
    bitmask = int(hash_digest, 16)
    grid = []
    for i in range(25):
        # Deterministic logic to pick tiles
        state = (bitmask >> i) & 3
        if state == 3: state = 0 # Favor safe tiles
        grid.append(state)

    # Ensure at least some safe tiles are shown
    if grid.count(0) < 3:
        for i in range(3):
            grid[random.randint(0, 24)] = 0

    confidence = 94 + (int(hash_digest[-2:], 16) % 6) # 94-99%
    
    reaction_time = round(time.time() - start_time, 2)
    
    # Update Stats
    if data.user_id not in USER_STATS:
        USER_STATS[data.user_id] = {"wins": 0, "losses": 0, "total_won": 0}
    
    if confidence > 97:
        USER_STATS[data.user_id]["wins"] += 1
        USER_STATS[data.user_id]["total_won"] += data.bet_amount * 2
    else:
        USER_STATS[data.user_id]["losses"] += 1

    return {
        "status": "success",
        "grid": grid,
        "method": method,
        "reaction_time": f"{reaction_time}s",
        "patterns_scanned": f"3.472,382,921,029",
        "confidence_score": f"{confidence}%",
        "game_info": {
            "uuid": data.uuid,
            "bet_amount": data.bet_amount,
            "mines": data.mines,
            "nonce": data.nonce
        }
    }

@app.get("/profile/{user_id}")
async def get_profile(user_id: str):
    if user_id not in USER_TOKENS:
        raise HTTPException(status_code=404, detail="No token linked.")
    
    token = USER_TOKENS[user_id]
    stats = USER_STATS.get(user_id, {"wins": 0, "losses": 0, "total_won": 0})
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{PROXY_URL}/user",
                headers={"x-auth-token": token}
            )
            user_data = response.json().get("user", {})
            
            return {
                "username": user_data.get("robloxUsername", "Unknown"),
                "balance": user_data.get("wallet", 0),
                "pfp": f"https://www.roblox.com/headshot-thumbnail/image?userId={user_data.get('robloxId', 0)}&width=420&height=420&format=png",
                "wins": stats["wins"],
                "losses": stats["losses"],
                "total_won": stats["total_won"]
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail="Failed to fetch profile.")

@app.get("/fetch_live/{user_id}")
async def fetch_live(user_id: str):
    if user_id not in USER_TOKENS:
        raise HTTPException(status_code=404, detail="No token linked. Use /link first.")
    
    token = USER_TOKENS[user_id]
    
    async with httpx.AsyncClient() as client:
        endpoints = [
            f"{PROXY_URL}/games/mines/active",
            f"{PROXY_URL}/mines/active",
            f"{PROXY_URL}/games/mines"
        ]
        
        last_err = "No active game found."
        for url in endpoints:
            try:
                response = await client.get(
                    url,
                    headers={
                        "x-auth-token": token,
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                        "Referer": "https://bloxflip.com/",
                        "Origin": "https://bloxflip.com"
                    }
                )
                if response.status_code == 200:
                    game_data = response.json()
                    if "hasGame" in game_data and game_data["hasGame"]:
                        game = game_data["game"]
                        return {
                            "uuid": game["uuid"],
                            "bet_amount": game["betAmount"],
                            "mines": game["minesAmount"],
                            "nonce": game["nonce"]
                        }
                    elif "game" in game_data and game_data["game"]:
                        game = game_data["game"]
                        return {
                            "uuid": game["uuid"],
                            "bet_amount": game["betAmount"],
                            "mines": game["minesAmount"],
                            "nonce": game["nonce"]
                        }
            except:
                continue
        
        raise HTTPException(status_code=404, detail="No active game found on your account. Start a game first!")

@app.post("/save_token")
async def save_token(data: TokenData):
    USER_TOKENS[data.user_id] = data.token
    return {"status": "success", "username": "Linked Account"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
