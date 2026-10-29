import uvicorn

if __name__ == "__main__":
    # One process owns the vehicle supervisor. Never add multiple API workers.
    uvicorn.run("taxi.api:create_app", factory=True, host="127.0.0.1", port=8000, workers=1)
