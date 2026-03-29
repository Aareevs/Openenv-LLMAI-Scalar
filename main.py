from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

# ---- Dummy Models (Phase 1 only) ----
class Action(BaseModel):
    type: str
    content: str = ""

# ---- Dummy State ----
env_state = {
    "step": 0
}

# ---- Endpoints ----

@app.get("/")
def root():
    return {"status": "Vault Sanitizer running"}

@app.post("/reset")
def reset():
    env_state["step"] = 0
    return {
        "observation": {
            "data_chunk": "Sample text with email test@gmail.com",
            "risk_report": ["Possible email detected"],
            "attempts_left": 3
        }
    }

@app.post("/step")
def step(action: Action):
    env_state["step"] += 1

    return {
        "observation": {
            "data_chunk": "Updated sample",
            "risk_report": [],
            "attempts_left": 2
        },
        "reward": {
            "score": 0.5
        },
        "done": False,
        "info": {}
    }
