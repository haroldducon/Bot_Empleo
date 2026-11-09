from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.routers import ai_keys, auth, gmail, jobs, profile

app = FastAPI(title="Nexo Laboral", docs_url="/docs", redoc_url=None)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

@app.middleware("http")
async def security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Cache-Control"] = "no-store" if request.url.path.startswith(("/auth", "/profile", "/ai-keys", "/gmail")) else "no-cache"
    return response

app.include_router(auth.router)
app.include_router(profile.router)
app.include_router(ai_keys.router)
app.include_router(gmail.router)
app.include_router(jobs.router)

@app.get("/health")
def health():
    return {"status": "ok"}
