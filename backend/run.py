import os
import uvicorn
from app.config import settings

if __name__ == "__main__":
    # Ensure backend always binds to 8000 internally so Next.js on $PORT can proxy to it
    backend_port = int(os.environ.get("FASTAPI_PORT", 8000))
    print(f"🚀 Starting FastAPI backend on {settings.HOST}:{backend_port}")
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=backend_port,
        reload=False,
        log_level="info",
    )
