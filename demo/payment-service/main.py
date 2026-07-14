# asyncio lets us "wait" without freezing the whole program (used to fake slowness).
import asyncio
# random lets us pick something unpredictable (used to fake occasional errors).
import random

# FastAPI is the toolkit that turns Python functions into web addresses.
# HTTPException is how we tell a visitor "something went wrong" with a specific error code.
from fastapi import FastAPI, HTTPException
# CORSMiddleware is the "permission slip" that lets our website (a different address)
# be allowed to ask this backend for data.
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    # Matches http://localhost:<any port>, so it keeps working no matter which
    # port Vite happens to pick for the dev server.
    allow_origin_regex=r"http://localhost:\d+",
    allow_methods=["*"],
    allow_headers=["*"],
)

# This is our "light switch": healthy, slow, erroring, or down.
# It lives only in memory, so it resets to "healthy" every time we restart this service.
state = {"mode": "healthy"}


# GET /health = "are you alive and working right now?"
@app.get("/health")
async def health():
    # Switch set to "down" -> refuse to answer, like a machine that's unplugged.
    if state["mode"] == "down":
        raise HTTPException(status_code=503, detail="service unavailable")

    # Switch set to "slow" -> pause for 2 seconds before replying, faking a sluggish service.
    if state["mode"] == "slow":
        await asyncio.sleep(2)

    # Switch set to "erroring" -> fail about half the time, faking a flaky service.
    if state["mode"] == "erroring" and random.random() < 0.5:
        raise HTTPException(status_code=500, detail="internal error")

    return {"status": "ok", "service": "payment-service", "mode": state["mode"]}


# GET /ready = "are you fully set up and able to take real work?"
# Similar to /health, but real systems use it for a slightly different question.
@app.get("/ready")
async def ready():
    return {"ready": state["mode"] != "down"}


# The four routes below are our "remote control buttons" - each one just
# flips the light switch to a different position, then confirms the new setting.

@app.post("/simulate/latency")
def simulate_latency():
    state["mode"] = "slow"
    return {"mode": state["mode"]}


@app.post("/simulate/errors")
def simulate_errors():
    state["mode"] = "erroring"
    return {"mode": state["mode"]}


@app.post("/simulate/down")
def simulate_down():
    state["mode"] = "down"
    return {"mode": state["mode"]}


@app.post("/restore")
def restore():
    state["mode"] = "healthy"
    return {"mode": state["mode"]}
