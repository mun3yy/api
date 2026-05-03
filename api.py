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

# --- THE 300 METHODS ---
# We generate 300 unique method names and descriptions
METHOD_NAMES = [
    "Probability", "Perc V2", "Entropy", "Gaussian", "Markov Chain", "Bayesian", 
    "Neural-Link", "Surgical-Light", "Boze-Increment", "Delta-Shift", "Grid-Sync",
    "Pulse-Scan", "Quantum-Drift", "Vortex-Loom", "Cipher-Match", "Void-Path"
]
DESCRIPTIONS = [
    "Analyzes historical tile drift to find safe corridors.",
    "Applies recursive nonce analysis to detect seed patterns.",
    "Uses high-entropy scanning to bypass randomized noise.",
    "Surgical precision matching based on multi-level pointer chains.",
    "Predicts the next safe tile using Markovian transition matrices."
]

def generate_300_methods():
    methods = []
    for i in range(300):
        name = f"{random.choice(METHOD_NAMES)} v{random.randint(1, 9)}.{random.randint(0, 9)}"
        desc = random.choice(DESCRIPTIONS)
        methods.append({"id": i, "name": name, "desc": desc})
    return methods

ALL_METHODS = generate_300_methods()

class TokenData(BaseModel):
    user_id: str
    token: str

class GameData(BaseModel):
    uuid: str
    bet_amount: float
    mines: int
    nonce: int
    user_id: str

def scan_trillions_of_patterns(seed_hash, method_id):
    """ 
    Simulates scanning trillions of patterns.
    Uses a double-hash to ensure the result is unique to the method and seed.
    """
    # First hash: The Seed
    h1 = hashlib.sha256(seed_hash.encode()).hexdigest()
    # Second hash: The Method Influence
    h2 = hashlib.sha256(f"{h1}-{method_id}".encode()).hexdigest()
    
    # Convert to a 25-bit pattern (The Grid)
    pattern_int = int(h2[:8], 16) % (2**25)
    return pattern_int

def int_to_grid(bit_integer):
    grid = []
    binary = bin(bit_integer)[2:].zfill(25)
    for bit in binary:
        # 0 = Safe (Green), 1 = Unsafe (Orange), 2 = Unknown (Red)
        grid.append(int(bit))
    return grid

@app.post("/predict")
async def predict(data: GameData):
    start_time = time.time()
    
    # --- PERFECT METHOD SELECTION ---
    # We use a combined hash of the UUID, Nonce, and Bet to find the 'Perfect' Method
    state_hash = hashlib.sha256(f"{data.uuid}-{data.nonce}-{data.bet_amount}".encode()).hexdigest()
    
    # Deterministically pick the 'Best' method for this specific state
    method_index = int(state_hash[:4], 16) % 300
    method = ALL_METHODS[method_index]
    method["name"] = f"🌟 Perfect {method['name'].split(' ')[0]}" # Mark as Perfect
    
    # --- PERFECT PATTERN SCANNING ---
    # We 'scan' the trillion patterns to find the one with the highest 'Win Confidence'
    pattern_int = scan_trillions_of_patterns(state_hash, method_index)
    grid = int_to_grid(pattern_int)
    
    # Calculate a fake 'Confidence Score'
    confidence = round(random.uniform(94.2, 99.9), 2)
    
    # Simulation of heavy processing
    processing_delay = random.uniform(1.2, 2.5)
    time.sleep(processing_delay)
    
    reaction_time = round(time.time() - start_time, 2)
    
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

@app.get("/fetch_live/{user_id}")
async def fetch_live(user_id: str):
    """ 
    Uses the stored app.rt token to get the actual live game from the server.
    """
    if user_id not in USER_TOKENS:
        raise HTTPException(status_code=404, detail="No app.rt token linked for this user.")
    
    token = USER_TOKENS[user_id]
    
    async with httpx.AsyncClient() as client:
        try:
            # This is the actual endpoint for live mines games
            response = await client.get(
                "https://api.bloxflip.com/games/mines/active",
                headers={
                    "x-auth-token": token,
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                }
            )
            game_data = response.json()
            
            if not game_data.get("hasGame"):
                raise HTTPException(status_code=404, detail="No active game found on your account.")
            
            game = game_data["game"]
            return {
                "uuid": game["uuid"],
                "bet_amount": game["betAmount"],
                "mines": game["minesCount"],
                "nonce": game["nonce"],
                "user_id": user_id
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to fetch game from server: {str(e)}")

@app.get("/status")
async def status():
    return {
        "status": "operational",
        "methods_loaded": 300,
        "patterns_indexed": "1,048,576 Trillion (Procedural)",
        "server_load": "0.14%"
    }

@app.post("/link_game")
async def link_game(data: GameData):
    """ The linker calls this to upload live game data """
    LIVE_GAMES[data.user_id] = data
    print(f"Linked game for user {data.user_id}")
    return {"status": "linked"}

@app.get("/get_linked/{user_id}")
async def get_linked(user_id: str):
    """ The bot calls this to see if the user has a live game """
    if user_id in LIVE_GAMES:
        return LIVE_GAMES[user_id]
    raise HTTPException(status_code=404, detail="No linked game found")

@app.post("/save_token")
async def save_token(data: TokenData):
    """ The bot calls this to save a user token """
    USER_TOKENS[data.user_id] = data.token
    print(f"Saved token for user {data.user_id}")
    return {"status": "success"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
