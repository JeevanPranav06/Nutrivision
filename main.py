from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routes.scan import router as scan_router
from routes.foods import router as foods_router
from routes.exercise import router as exercise_router
from routes.user import router as user_router

app = FastAPI(title="Nutrivision API")

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routes
app.include_router(scan_router, prefix="/scan", tags=["Scan"])
app.include_router(foods_router, prefix="/foods", tags=["Foods"])
app.include_router(exercise_router, prefix="/exercise", tags=["Exercise"])
app.include_router(user_router, prefix="/user", tags=["User"])

@app.get("/")
def root():
    return {"message": "Nutrivision API running"}
