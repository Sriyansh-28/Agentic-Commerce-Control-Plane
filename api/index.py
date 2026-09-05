from backend.main import app


@app.middleware("http")
async def strip_vercel_api_prefix(request, call_next):
    """
    Vercel routes /api/* requests to this FastAPI function.

    The existing application routes intentionally remain unchanged
    so local development continues to use:
        /agent/purchase
        /transactions/start
        /transactions/execute
        ...

    Vercel therefore strips the /api prefix before FastAPI routing.
    """
    path = request.scope.get("path", "")

    if path == "/api":
        request.scope["path"] = "/"
    elif path.startswith("/api/"):
        request.scope["path"] = path[4:]

    response = await call_next(request)
    return response