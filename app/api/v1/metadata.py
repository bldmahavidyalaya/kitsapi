"""
API metadata and statistics endpoints
"""
from datetime import datetime
from fastapi import APIRouter, Request
from typing import Dict, Any

router = APIRouter()

# Store metrics
metrics = {
    "total_requests": 0,
    "total_conversions": 0,
    "failed_conversions": 0,
    "start_time": datetime.utcnow()
}


@router.get("/metadata", tags=["Metadata"])
def api_metadata() -> Dict[str, Any]:
    """Get API metadata and version information"""
    return {
        "name": "Kits API",
        "version": "1.0.0",
        "description": "Production-grade file conversion API with 86+ endpoints",
        "status": "active",
        "environment": "production",
        "endpoints": {
            "document": 15,
            "image": 11,
            "audio": 16,
            "video": 18,
            "data": 6,
            "security": 13,
            "utilities": 6,
            "social_media": 1,
            "archive": 2
        },
        "total_endpoints": 88,
        "api_docs": "/docs",
        "openapi_schema": "/openapi.json"
    }


@router.get("/stats", tags=["Metrics"])
def api_stats() -> Dict[str, Any]:
    """Get API usage statistics"""
    uptime = datetime.utcnow() - metrics["start_time"]
    success_rate = 0
    if metrics["total_conversions"] > 0:
        success_rate = ((metrics["total_conversions"] - metrics["failed_conversions"]) 
                       / metrics["total_conversions"] * 100)
    
    return {
        "uptime_seconds": int(uptime.total_seconds()),
        "total_requests": metrics["total_requests"],
        "total_conversions": metrics["total_conversions"],
        "failed_conversions": metrics["failed_conversions"],
        "success_rate_percent": round(success_rate, 2),
        "start_time": metrics["start_time"].isoformat()
    }


@router.get("/features", tags=["Metadata"])
def list_features() -> Dict[str, Any]:
    """List all available features and capabilities"""
    return {
        "document_processing": {
            "pdf_conversion": True,
            "ocr": True,
            "metadata_removal": True,
            "encryption": True,
            "compression": True
        },
        "image_processing": {
            "format_conversion": True,
            "resizing": True,
            "effects": True,
            "watermarking": True,
            "color_correction": True
        },
        "audio_processing": {
            "format_conversion": True,
            "noise_removal": True,
            "normalization": True,
            "effects": True
        },
        "video_processing": {
            "format_conversion": True,
            "compression": True,
            "effects": True,
            "frame_extraction": True
        },
        "security": {
            "encryption": True,
            "pii_detection": True,
            "gdpr_compliance": True,
            "integrity_verification": True
        },
        "cloud_integration": {
            "aws_s3": True,
            "social_media": True
        }
    }


@router.post("/metrics/record", tags=["Metrics"], include_in_schema=False)
def record_metric(endpoint: str, status: str):
    """Record conversion metric (internal use)"""
    metrics["total_requests"] += 1
    if status == "success":
        metrics["total_conversions"] += 1
    elif status == "failed":
        metrics["failed_conversions"] += 1
    return {"status": "recorded"}
