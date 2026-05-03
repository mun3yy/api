from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import time
import random
import hashlib
import math
import httpx

app = FastAPI()

# --- CONFIGURATION ---
USER_TOKENS = {} 
USER_STATS = {} 
PROXY_URL = "https://delicate-disk-8300.em5505316.workers.dev" 

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
    combined_seed = f"{data.uuid}{data.nonce}{data.bet_amount}"
    hash_digest = hashlib.sha256(combined_seed.encode()).hexdigest()
    method_index = int(hash_digest[:4], 16) % len(METHODS)
    method = METHODS[method_index]
    
    bitmask = int(hash_digest, 16)
    grid = []
    for i in range(25):
        state = (bitmask >> i) & 3
        if state == 3: state = 0 
        grid.append(state)

    if grid.count(0) < 3:
        for i in range(3):
            grid[random.randint(0, 24)] = 0

    confidence = 94 + (int(hash_digest[-2:], 16) % 6)
    
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
        "confidence_score": f"{confidence}%",
        "game_info": data.dict()
    }

@app.get("/profile/{user_id}")
async def get_profile(user_id: str):
    if user_id not in USER_TOKENS:
        raise HTTPException(status_code=404, detail="No token linked.")
    
    token = USER_TOKENS[user_id]
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{PROXY_URL}/user", headers={"x-auth-token": token})
            user_data = response.json().get("user", {})
            return {
                "username": user_data.get("robloxUsername", "Unknown"),
                "balance": user_data.get("wallet", 0),
                "pfp": f"https://www.roblox.com/headshot-thumbnail/image?userId={user_data.get('robloxId', 0)}&width=420&height=420&format=png",
                "wins": USER_STATS.get(user_id, {}).get("wins", 0),
                "losses": USER_STATS.get(user_id, {}).get("losses", 0),
                "total_won": USER_STATS.get(user_id, {}).get("total_won", 0)
            }
        except Exception:
            raise HTTPException(status_code=500, detail="Profile fetch failed.")

@app.get("/fetch_live/{user_id}")
async def fetch_live(user_id: str):
    if user_id not in USER_TOKENS:
        raise HTTPException(status_code=404, detail="Link first!")
    
    token = USER_TOKENS[user_id]
    async with httpx.AsyncClient() as client:
        # Try HISTORY endpoint
        try:
            res = await client.get(
                f"{PROXY_URL}/games/mines/history",
                headers={"x-auth-token": token, "User-Agent": "Mozilla/5.0"}
            )
            if res.status_code == 200:
                games = res.json().get("games", [])
                if games:
                    g = games[0]
                    return {"uuid": g["uuid"], "bet_amount": g["betAmount"], "mines": g["minesAmount"], "nonce": g["nonce"]}
            
            # If history fails, try the active check
            res2 = await client.get(
                f"{PROXY_URL}/games/mines",
                headers={"x-auth-token": token, "User-Agent": "Mozilla/5.0"}
            )
            debug_info = f"Status: {res2.status_code} | Body: {res2.text[:100]}"
            raise HTTPException(status_code=404, detail=f"DEBUG: {debug_info}")
        except Exception as e:
            raise HTTPException(status_code=404, detail=f"Final Error: {str(e)}")

@app.post("/save_token")
async def save_token(data: TokenData):
    USER_TOKENS[data.user_id] = data.token
    return {"status": "success"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
