"""
Health check and diagnostics endpoints
"""
from datetime import datetime, timezone
from fastapi import APIRouter
import shutil

router = APIRouter()


def _get_utc_now() -> str:
    """Get current UTC timestamp as ISO string"""
    return datetime.now(timezone.utc).isoformat()


def _check_database():
    """Check database connectivity"""
    try:
        from app.db.session import engine
        with engine.connect() as conn:
            conn.execute("SELECT 1")
        return {"status": "healthy", "message": "Database connected"}
    except Exception as e:
        return {"status": "unhealthy", "message": str(e)}


def _check_storage():
    """Check available storage"""
    try:
        total, used, free = shutil.disk_usage("/")
        percent_used = (used / total) * 100
        return {
            "status": "healthy" if percent_used < 90 else "warning",
            "total_gb": round(total / (1024**3), 2),
            "used_gb": round(used / (1024**3), 2),
            "free_gb": round(free / (1024**3), 2),
            "percent_used": round(percent_used, 2)
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.get("/health", summary="Health check", response_model=dict)
def health_check():
    """Basic health check endpoint"""
    return {
        "status": "ok",
        "version": "1.0.0",
        "timestamp": _get_utc_now()
    }


@router.get("/health/detailed", summary="Detailed health check", response_model=dict)
def health_detailed():
    """Detailed health check with system diagnostics"""
    return {
        "status": "ok",
        "version": "1.0.0",
        "timestamp": _get_utc_now(),
        "database": _check_database(),
        "storage": _check_storage()
    }


@router.get("/health/ready", summary="Readiness probe", response_model=dict)
def readiness_check():
    """Readiness probe for Kubernetes/orchestration"""
    db_check = _check_database()
    storage_check = _check_storage()
    
    ready = (
        db_check['status'] == 'healthy' and
        storage_check['status'] != 'error'
    )
    
    return {
        "ready": ready,
        "checks": {
            "database": db_check,
            "storage": storage_check
        }
    }


@router.get("/health/live", summary="Liveness probe", response_model=dict)
def liveness_check():
    """Liveness probe for Kubernetes/orchestration"""
    return {"alive": True, "timestamp": _get_utc_now()}
