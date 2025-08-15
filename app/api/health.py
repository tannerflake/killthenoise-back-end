from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from app.services.connection_service import ConnectionService, create_connection_service

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/")
@router.get("")
@router.get("/health")
async def health_check():
    """Basic health check endpoint."""
    return {"status": "healthy", "message": "Service is running"}


@router.get("/connections")
async def test_connections(
    connection_service: ConnectionService = Depends(create_connection_service)
):
    """Test all external service connections."""
    try:
        results = await connection_service.test_all_connections()
        summary = connection_service.get_connection_summary(results)
        
        return JSONResponse(
            content=summary,
            status_code=200 if summary["success_rate"] == 100 else 503
        )
    except Exception as e:
        return JSONResponse(
            content={
                "error": "Failed to test connections",
                "message": str(e),
                "total_tests": 0,
                "successful_tests": 0,
                "failed_tests": 0,
                "success_rate": 0,
                "average_response_time": 0,
                "results": []
            },
            status_code=500
        )





@router.get("/connections/hubspot")
async def test_hubspot_connection(
    connection_service: ConnectionService = Depends(create_connection_service)
):
    """Test HubSpot connection specifically."""
    try:
        result = await connection_service.test_hubspot_connection()
        return JSONResponse(
            content=result.to_dict(),
            status_code=200 if result.success else 503
        )
    except Exception as e:
        return JSONResponse(
            content={
                "service": "HubSpot",
                "success": False,
                "response_time": 0,
                "error": str(e)
            },
            status_code=500
        )


@router.get("/connections/claude")
async def test_claude_connection(
    connection_service: ConnectionService = Depends(create_connection_service)
):
    """Test Claude API connection specifically."""
    try:
        result = await connection_service.test_claude_connection()
        return JSONResponse(
            content=result.to_dict(),
            status_code=200 if result.success else 503
        )
    except Exception as e:
        return JSONResponse(
            content={
                "service": "Claude API",
                "success": False,
                "response_time": 0,
                "error": str(e)
            },
            status_code=500
        )


@router.get("/connections/supabase")
async def test_supabase_connection(
    connection_service: ConnectionService = Depends(create_connection_service)
):
    """Test Supabase connection specifically."""
    try:
        result = await connection_service.test_supabase_connection()
        return JSONResponse(
            content=result.to_dict(),
            status_code=200 if result.success else 503
        )
    except Exception as e:
        return JSONResponse(
            content={
                "service": "Supabase",
                "success": False,
                "response_time": 0,
                "error": str(e)
            },
            status_code=500
        ) 