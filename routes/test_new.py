"""Test router"""
from fastapi import APIRouter

router = APIRouter(prefix="/test-new", tags=["Test"])

@router.get("/hello")
async def test_hello():
    return {"message": "hello from test router"}
