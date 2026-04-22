from fastapi import APIRouter
 
router = APIRouter()
 
 
@router.get("/")
async def root():
    """Root endpoint."""
    return {"status": "ok"}
 
 
@router.get("/health/live")
async def liveness():
    """Liveness probe — is the process running?"""
    return {"status": "alive"}
 