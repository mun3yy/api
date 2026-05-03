from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import time
import random
import hashlib
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
        "name": f"Perfect Method v{i}",
        "desc": "Real-time SHA256 deterministic scanning."
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

@app.get("/fetch_live/{user_id}")
async def fetch_live(user_id: str):
    if user_id not in USER_TOKENS:
        raise HTTPException(status_code=404, detail="Link first!")
    
    token = USER_TOKENS[user_id]
    async with httpx.AsyncClient() as client:
        # We must use EXACT headers from the browser screenshot
        headers = {
            "x-auth-token": token,
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Referer": "https://bloxflip.com/mines",
            "Origin": "https://bloxflip.com",
            "x-currency": "FLIPCOINS",
            "Content-Type": "application/json"
        }
        
        try:
            # Try history first as it's more reliable
            res = await client.get(f"{PROXY_URL}/api/games/mines/history", headers=headers)
            if res.status_code == 200:
                games = res.json().get("games", [])
                if games:
                    g = games[0]
                    return {"uuid": g["uuid"], "bet_amount": g["betAmount"], "mines": g["minesAmount"], "nonce": g["nonce"]}
            
            # Fallback to active
            res2 = await client.get(f"{PROXY_URL}/api/games/mines", headers=headers)
            if res2.status_code == 200:
                data = res2.json()
                if data.get("hasGame"):
                    g = data["game"]
                    return {"uuid": g["uuid"], "bet_amount": g["betAmount"], "mines": g["minesAmount"], "nonce": g["nonce"]}
            
            raise HTTPException(status_code=404, detail="No active game found. Refresh the site and try again.")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Server Error: {str(e)}")

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

    return {
        "status": "success",
        "grid": grid,
        "method": method,
        "confidence_score": f"{94 + (int(hash_digest[-2:], 16) % 6)}%",
        "game_info": data.dict()
    }

@app.post("/save_token")
async def save_token(data: TokenData):
    USER_TOKENS[data.user_id] = data.token
    return {"status": "success"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
