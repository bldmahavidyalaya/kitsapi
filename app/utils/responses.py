"""
Enhanced API response utilities for consistent formatting and error handling
"""
from typing import Any, Dict, Optional
from datetime import datetime, timezone
from fastapi import HTTPException
from pydantic import BaseModel
import logging

logger = logging.getLogger(__name__)


class APIResponse(BaseModel):
    """Standard API response format"""
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    timestamp: str = None
    
    def __init__(self, **data):
        if 'timestamp' not in data:
            data['timestamp'] = datetime.now(timezone.utc).isoformat()
        super().__init__(**data)


def success_response(data: Any = None, **kwargs) -> Dict[str, Any]:
    """Create a success response"""
    return {
        "success": True,
        "data": data,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        **kwargs
    }


def error_response(
    message: str, 
    status_code: int = 500, 
    details: Optional[Dict] = None
) -> HTTPException:
    """Create an error response and raise exception"""
    error_data = {
        "success": False,
        "error": message,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    if details:
        error_data["details"] = details
    
    logger.error(f"API Error: {message} - {details}")
    raise HTTPException(status_code=status_code, detail=error_data)


def validate_input(value: Any, field_name: str, required: bool = True) -> Any:
    """Validate input parameter"""
    if required and not value:
        raise error_response(
            f"Missing required field: {field_name}",
            status_code=400,
            details={"field": field_name}
        )
    return value


class PerformanceMetrics(BaseModel):
    """Performance metrics for conversion operations"""
    processing_time_ms: float
    input_size_bytes: int
    output_size_bytes: int
    compression_ratio: Optional[float] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "processing_time_ms": 125.5,
                "input_size_bytes": 1024000,
                "output_size_bytes": 512000,
                "compression_ratio": 0.5
            }
        }
