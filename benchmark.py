#!/usr/bin/env python3
"""
Performance benchmarking script for Kits API
"""
import asyncio
import time
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import tempfile
from PIL import Image
import io
import json

BASE_URL = "http://localhost:8000/api/v1"

def benchmark_sequential(num_requests: int = 10) -> dict:
    """Benchmark sequential requests"""
    print(f"\n📊 Sequential Benchmark ({num_requests} requests)")
    
    times = []
    for i in range(num_requests):
        start = time.time()
        try:
            response = requests.get(f"{BASE_URL}/health")
            elapsed = time.time() - start
            times.append(elapsed)
            print(f"  Request {i+1}: {elapsed*1000:.2f}ms")
        except Exception as e:
            print(f"  Request {i+1}: ERROR - {e}")
    
    if times:
        avg_time = sum(times) / len(times)
        min_time = min(times)
        max_time = max(times)
        total_time = sum(times)
        return {
            "type": "sequential",
            "requests": num_requests,
            "avg_ms": avg_time * 1000,
            "min_ms": min_time * 1000,
            "max_ms": max_time * 1000,
            "total_ms": total_time * 1000,
            "rps": num_requests / total_time
        }
    return {}


def benchmark_concurrent(num_requests: int = 20, max_workers: int = 5) -> dict:
    """Benchmark concurrent requests"""
    print(f"\n📊 Concurrent Benchmark ({num_requests} requests, {max_workers} workers)")
    
    times = []
    start_total = time.time()
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = []
        for i in range(num_requests):
            future = executor.submit(
                lambda idx=i: (idx, requests.get(f"{BASE_URL}/health"))
            )
            futures.append(future)
        
        for future in as_completed(futures):
            try:
                idx, response = future.result()
                elapsed = time.time() - start_total
                times.append(elapsed)
                print(f"  Request {idx+1}: {response.status_code} ({elapsed*1000:.2f}ms)")
            except Exception as e:
                print(f"  Request ERROR: {e}")
    
    total_time = time.time() - start_total
    
    if times:
        avg_time = sum(times) / len(times)
        return {
            "type": "concurrent",
            "requests": num_requests,
            "workers": max_workers,
            "avg_ms": avg_time * 1000,
            "min_ms": min(times) * 1000,
            "max_ms": max(times) * 1000,
            "total_ms": total_time * 1000,
            "rps": num_requests / total_time
        }
    return {}


def benchmark_file_upload() -> dict:
    """Benchmark file upload and conversion"""
    print(f"\n📊 File Upload Benchmark")
    
    # Create test image
    img = Image.new('RGB', (1000, 1000), color=(73, 109, 137))
    
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes.seek(0)
    
    start = time.time()
    try:
        files = {'file': ('test.png', img_bytes, 'image/png')}
        data = {'target': 'jpg', 'quality': '85'}
        
        response = requests.post(
            f"{BASE_URL}/convert/image-convert",
            files=files,
            data=data
        )
        elapsed = time.time() - start
        
        size_bytes = len(img_bytes.getvalue())
        
        print(f"  Status: {response.status_code}")
        print(f"  Input size: {size_bytes / 1024:.2f} KB")
        print(f"  Processing time: {elapsed*1000:.2f}ms")
        
        return {
            "type": "file_upload",
            "operation": "image_conversion",
            "input_size_bytes": size_bytes,
            "processing_time_ms": elapsed * 1000,
            "status": response.status_code
        }
    except Exception as e:
        print(f"  ERROR: {e}")
        elapsed = time.time() - start
        return {
            "type": "file_upload",
            "error": str(e),
            "processing_time_ms": elapsed * 1000
        }


def benchmark_api_endpoints() -> dict:
    """Benchmark various API endpoints"""
    print(f"\n📊 Endpoint Benchmark")
    
    endpoints = [
        ("Health Check", f"{BASE_URL}/health"),
        ("Health Detailed", f"{BASE_URL}/health/detailed"),
        ("Metadata", f"{BASE_URL}/metadata"),
        ("Stats", f"{BASE_URL}/stats"),
        ("Features", f"{BASE_URL}/features"),
    ]
    
    results = {}
    for name, url in endpoints:
        start = time.time()
        try:
            response = requests.get(url)
            elapsed = time.time() - start
            results[name] = {
                "status": response.status_code,
                "time_ms": elapsed * 1000,
                "size_bytes": len(response.content)
            }
            print(f"  {name}: {elapsed*1000:.2f}ms ({response.status_code})")
        except Exception as e:
            print(f"  {name}: ERROR - {e}")
            results[name] = {"error": str(e)}
    
    return results


def main():
    """Run all benchmarks"""
    print("🚀 Kits API Performance Benchmark")
    print("=" * 50)
    
    results = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "benchmarks": {}
    }
    
    # Sequential benchmark
    seq_result = benchmark_sequential(num_requests=10)
    if seq_result:
        results["benchmarks"]["sequential"] = seq_result
        print(f"\n✅ Avg: {seq_result['avg_ms']:.2f}ms | RPS: {seq_result['rps']:.2f}")
    
    # Concurrent benchmark
    conc_result = benchmark_concurrent(num_requests=20, max_workers=5)
    if conc_result:
        results["benchmarks"]["concurrent"] = conc_result
        print(f"\n✅ Avg: {conc_result['avg_ms']:.2f}ms | RPS: {conc_result['rps']:.2f}")
    
    # Endpoint benchmark
    endpoint_result = benchmark_api_endpoints()
    results["benchmarks"]["endpoints"] = endpoint_result
    
    # File upload benchmark
    try:
        file_result = benchmark_file_upload()
        results["benchmarks"]["file_upload"] = file_result
    except Exception as e:
        print(f"\n⚠️  File upload benchmark skipped: {e}")
    
    # Summary
    print("\n" + "=" * 50)
    print("📈 Benchmark Summary")
    print("=" * 50)
    
    if "sequential" in results["benchmarks"]:
        seq = results["benchmarks"]["sequential"]
        print(f"Sequential (10 req):  {seq['avg_ms']:.2f}ms avg, {seq['rps']:.2f} req/sec")
    
    if "concurrent" in results["benchmarks"]:
        conc = results["benchmarks"]["concurrent"]
        print(f"Concurrent (20 req, 5 workers): {conc['avg_ms']:.2f}ms avg, {conc['rps']:.2f} req/sec")
    
    # Save results
    with open("/workspaces/kitsapi/benchmark_results.json", "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"\n✅ Results saved to benchmark_results.json")
    print("=" * 50)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n⚠️  Benchmark interrupted by user")
    except ConnectionError:
        print("\n❌ Error: Could not connect to API at", BASE_URL)
        print("Please ensure the API is running: python -m uvicorn app.main:app --host 0.0.0.0 --port 8000")
