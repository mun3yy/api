from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict
import time
import hashlib
from collections import defaultdict, Counter

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── IN-MEMORY CACHE ─────────────────────────────────────────────────────────

# Store user profile from browser { user_id: { username, balance, avatar } }
CACHED_PROFILES: Dict[str, dict] = {}

# Store active game from browser { user_id: { uuid, nonce, bet_amount, mines } }
CACHED_ACTIVE: Dict[str, dict] = {}

# In-memory history store: { user_id: [game, game, ...] }
GAME_HISTORY: Dict[str, List[dict]] = defaultdict(list)
MAX_HISTORY = 200

# ─── MODELS ──────────────────────────────────────────────────────────────────

class SyncProfileReq(BaseModel):
    user_id: str
    profile: dict

class SyncHistoryReq(BaseModel):
    user_id: str
    games: list

class SyncActiveReq(BaseModel):
    user_id: str
    game: dict

class PredictionRequest(BaseModel):
    user_id: str

# ─── HELPERS ─────────────────────────────────────────────────────────────────

def parse_game(g: dict) -> dict:
    return {
        "uuid":       g.get("uuid") or g.get("id", ""),
        "bet_amount": g.get("betAmount") or g.get("bet_amount") or 0,
        "mines":      g.get("minesAmount") or g.get("mines_count") or g.get("mines") or 0,
        "nonce":      g.get("nonce") or 0,
        "has_ended":  g.get("has_ended", True),
        "profit":     g.get("profit") or g.get("winAmount") or 0,
        "created_at": g.get("createdAt") or g.get("created_at") or "",
    }

def store_history(user_id: str, games: list):
    existing_uuids = {g["uuid"] for g in GAME_HISTORY[user_id]}
    for g in games:
        parsed = parse_game(g)
        if parsed["uuid"] and parsed["uuid"] not in existing_uuids:
            GAME_HISTORY[user_id].append(parsed)
            existing_uuids.add(parsed["uuid"])
    GAME_HISTORY[user_id] = sorted(
        GAME_HISTORY[user_id],
        key=lambda x: x.get("created_at", ""),
        reverse=True
    )[:MAX_HISTORY]

def analyze_patterns(games: list) -> dict:
    if not games:
        return {}
    mine_counts = Counter(g["mines"] for g in games)
    nonce_mod = Counter(g["nonce"] % 5 for g in games if g.get("nonce"))
    total = len(games)
    wins = sum(1 for g in games if g.get("profit", 0) > 0)
    common_mines = mine_counts.most_common(1)[0][0] if mine_counts else 0
    even_nonces = sum(1 for g in games if g.get("nonce", 0) % 2 == 0)
    nonce_parity = "even" if even_nonces > total / 2 else "odd"
    
    return {
        "total_games": total,
        "win_rate": round(wins / total * 100, 1),
        "most_common_mines": common_mines,
        "nonce_parity_bias": nonce_parity,
    }

def generate_grid(uuid: str, nonce: int, bet: float, mines: int, patterns: dict) -> list:
    seed = f"{uuid}-{nonce}-{bet}-{mines}"
    h = int(hashlib.sha256(seed.encode()).hexdigest(), 16)
    grid = []
    for i in range(25):
        bits = (h >> (i * 2)) & 3
        if bits == 3: bits = 0
        grid.append(bits)

    if patterns.get("nonce_parity_bias"):
        parity = "even" if nonce % 2 == 0 else "odd"
        if parity == patterns["nonce_parity_bias"]:
            grid = [0 if v == 2 else v for v in grid]
    return grid

# ─── BROWSER SYNC ROUTES ─────────────────────────────────────────────────────

@app.post("/sync/profile")
async def sync_profile(data: SyncProfileReq):
    p = data.profile
    CACHED_PROFILES[data.user_id] = {
        "username": p.get("robloxUsername") or p.get("username") or "Unknown",
        "balance": p.get("wallet") or 0,
        "avatar": p.get("avatar") or "https://bloxflip.com/favicon.ico"
    }
    return {"status": "ok"}

@app.post("/sync/history")
async def sync_history(data: SyncHistoryReq):
    store_history(data.user_id, data.games)
    # Automatically find active game from history
    active = next((g for g in data.games if g.get("has_ended") == False), None)
    if active:
        CACHED_ACTIVE[data.user_id] = parse_game(active)
    return {"status": "ok"}

@app.post("/sync/active")
async def sync_active(data: SyncActiveReq):
    CACHED_ACTIVE[data.user_id] = parse_game(data.game)
    return {"status": "ok"}

# ─── DISCORD BOT ROUTES ──────────────────────────────────────────────────────

@app.get("/get_profile/{user_id}")
async def get_profile(user_id: str):
    if user_id not in CACHED_PROFILES:
        raise HTTPException(status_code=404, detail="No profile synced. Keep your browser tab open!")
    return CACHED_PROFILES[user_id]

@app.get("/history/{user_id}")
async def get_history(user_id: str):
    history = GAME_HISTORY.get(user_id, [])
    if not history:
        raise HTTPException(status_code=404, detail="No history synced. Open Bloxflip in your browser.")
    return {
        "total_fetched": len(history),
        "patterns": analyze_patterns(history)
    }

@app.post("/predict")
async def predict(data: PredictionRequest):
    start = time.time()
    
    if data.user_id not in CACHED_ACTIVE:
        raise HTTPException(status_code=404, detail="No active game found! Start a game on Bloxflip first.")
        
    active = CACHED_ACTIVE[data.user_id]
    
    # Check if game actually started
    if not active.get("uuid") or active.get("nonce") is None:
        raise HTTPException(status_code=400, detail="Active game invalid.")

    patterns = analyze_patterns(GAME_HISTORY.get(data.user_id, []))
    grid = generate_grid(active["uuid"], active["nonce"], active["bet_amount"], active["mines"], patterns)
    
    safe_tiles  = [i for i, v in enumerate(grid) if v == 0]
    recommended = max(1, min(len(safe_tiles), 10 - active["mines"]))

    confidence = 55 + (int(active["uuid"][-2:], 16) % 30)
    if patterns.get("total_games", 0) >= 20: confidence = min(confidence + 8, 91)

    return {
        "status": "success",
        "grid": grid,
        "recommended_clicks": recommended,
        "confidence": f"{confidence}%",
        "reaction_time": f"{round(time.time() - start, 4)}s",
        "pattern_bias_applied": bool(patterns),
        "game_info": active
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
