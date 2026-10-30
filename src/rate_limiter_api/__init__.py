def main() -> None:
    """Start the installed API with the same app as the Docker image."""
    import uvicorn

    uvicorn.run("app.main:app", host="127.0.0.1", port=8000)
