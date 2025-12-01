"""Simple test to see if routes work"""
from fastapi import FastAPI

app = FastAPI()

@app.get("/test")
async def test_route():
    return {"message": "Hello, World!"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
