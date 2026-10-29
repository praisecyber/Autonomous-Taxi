from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from taxi.routers.operator import router as operator_router
from taxi.routers.passenger import router as passenger_router # Add this line

app = FastAPI(title="Autonomous Taxi API")

app.include_router(operator_router)
app.include_router(passenger_router) # Mount Member 1's router[cite: 30, 37]

app.mount("/static", StaticFiles(directory="taxi/static"), name="static")

@app.get("/")
async def root():
    return {"message": "Taxi Backend Running."}