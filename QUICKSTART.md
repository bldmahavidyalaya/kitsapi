# Quick Start Guide - Kits API

## 🚀 Installation & Setup

### Prerequisites
- Python 3.10+
- pip or conda
- Git
- Docker (optional)

### 1. Clone Repository
```bash
cd /workspaces/kitsapi
git clone <repository-url> .
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Run Tests
```bash
python -m pytest tests/ -v
# Expected: 33 passed in ~1.8s
```

### 4. Start Development Server
```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Access the API:
- **OpenAPI Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/api/v1/health

---

## 📋 API Endpoints Overview

### Health & Status
```
GET  /api/v1/health              # Basic health check
GET  /api/v1/health/detailed     # Health with diagnostics
GET  /api/v1/health/ready        # Kubernetes readiness probe
GET  /api/v1/health/live         # Kubernetes liveness probe
```

### Metadata
```
GET  /api/v1/metadata            # API info and version
GET  /api/v1/stats               # Usage statistics
GET  /api/v1/features            # Available features
```

### Document Processing
```
POST /api/v1/convert/pdf-to-word          # PDF → Word (.docx)
POST /api/v1/convert/word-to-pdf          # Word → PDF
POST /api/v1/convert/pdf-to-excel         # PDF → Excel
POST /api/v1/convert/pdf-merge            # Merge PDFs
POST /api/v1/convert/pdf-split            # Split PDF
# ... 10+ more document endpoints
```

### Image Processing
```
POST /api/v1/convert/image-convert        # Convert image formats
POST /api/v1/convert/image-resize         # Resize image
POST /api/v1/convert/image-compress       # Compress image
POST /api/v1/convert/image-watermark      # Add watermark
# ... 7+ more image endpoints
```

### Audio Processing
```
POST /api/v1/convert/audio-convert        # Convert audio format
POST /api/v1/convert/audio-trim           # Trim audio
POST /api/v1/convert/audio-merge          # Merge audios
# ... 13+ more audio endpoints
```

### Data Conversions
```
POST /api/v1/convert/csv-to-json          # CSV → JSON
POST /api/v1/convert/json-to-csv          # JSON → CSV
POST /api/v1/convert/json-to-xml          # JSON → XML
# ... 3+ more data endpoints
```

### Security
```
POST /api/v1/convert/file-hash            # Generate file hash
POST /api/v1/convert/encrypt-file         # Encrypt file
POST /api/v1/convert/decrypt-file         # Decrypt file
# ... 10+ more security endpoints
```

### CRUD Operations
```
POST   /api/v1/items              # Create item
GET    /api/v1/items              # List items
GET    /api/v1/items/{id}         # Get item
PATCH  /api/v1/items/{id}         # Update item
DELETE /api/v1/items/{id}         # Delete item
```

---

## 🧪 Testing

### Run All Tests
```bash
python -m pytest tests/ -v
```

### Run Specific Test File
```bash
python -m pytest tests/test_api.py -v
python -m pytest tests/test_comprehensive.py -v
```

### Run Specific Test
```bash
python -m pytest tests/test_api.py::test_health -v
```

### Run with Coverage
```bash
python -m pytest tests/ --cov=app --cov-report=html
```

---

## 📊 Performance Benchmarking

### Run Benchmark Suite
```bash
python benchmark.py
```

This tests:
- Sequential request performance
- Concurrent request handling (5 workers)
- File upload and conversion
- Various API endpoints

Results saved to `benchmark_results.json`

---

## 🐳 Docker Deployment

### Build Image
```bash
docker build -t kitsapi:latest .
```

### Run Container
```bash
docker run -p 8000:8000 kitsapi:latest
```

### Using Docker Compose
```bash
docker-compose up -d
docker-compose logs -f
docker-compose down
```

---

## 🔄 Common API Usage Examples

### Convert Image to JPEG
```python
import requests

with open('image.png', 'rb') as f:
    files = {'file': f}
    data = {'target': 'jpg', 'quality': '85'}
    
    response = requests.post(
        'http://localhost:8000/api/v1/convert/image-convert',
        files=files,
        data=data
    )
    
    with open('output.jpg', 'wb') as out:
        out.write(response.content)
```

### Convert CSV to JSON
```python
import requests

with open('data.csv', 'rb') as f:
    files = {'file': f}
    
    response = requests.post(
        'http://localhost:8000/api/v1/convert/csv-to-json',
        files=files
    )
    
    json_data = response.json()
```

### Get API Statistics
```python
import requests

response = requests.get('http://localhost:8000/api/v1/stats')
stats = response.json()

print(f"Uptime: {stats['uptime_seconds']} seconds")
print(f"Success Rate: {stats['success_rate_percent']}%")
```

### Create Item (CRUD)
```python
import requests

data = {
    "name": "Test Item",
    "description": "Test Description",
    "price": 29.99
}

response = requests.post(
    'http://localhost:8000/api/v1/items',
    json=data
)

item = response.json()
print(f"Created item with ID: {item['id']}")
```

---

## 📁 Project Structure

```
kitsapi/
├── app/
│   ├── main.py                    # FastAPI app factory
│   ├── db/
│   │   └── session.py             # Database setup
│   ├── models/
│   │   └── item.py                # SQLModel definitions
│   ├── schemas/
│   │   └── item.py                # Pydantic schemas
│   ├── api/
│   │   └── v1/
│   │       ├── health.py          # Health endpoints
│   │       ├── items.py           # CRUD endpoints
│   │       ├── convert.py         # Core conversions
│   │       ├── convert_advanced.py        # Advanced conversions
│   │       ├── convert_advanced_extended.py # Extended conversions
│   │       └── metadata.py        # API metadata
│   ├── utils/
│   │   ├── file_handler.py        # File operations
│   │   ├── responses.py           # Response utilities
│   │   └── __init__.py
│   └── static/
├── tests/
│   ├── test_api.py                # Basic tests
│   └── test_comprehensive.py      # Integration tests
├── requirements.txt               # Dependencies
├── docker-compose.yml             # Docker setup
├── Dockerfile                     # Container config
├── README.md                      # Overview
├── DEPLOYMENT.md                  # Deployment guide
├── OPTIMIZATION.md                # Optimization details
├── PRODUCTION_READY.md            # Production checklist
└── benchmark.py                   # Performance benchmarks
```

---

## 🔧 Configuration

### Environment Variables
```bash
# Server
export PORT=8000
export HOST=0.0.0.0

# Database
export DATABASE_URL="sqlite:///./app.db"

# Performance
export MAX_CONCURRENT_CONVERSIONS=5
export CONVERSION_TIMEOUT=300

# Security
export ALLOWED_HOSTS="localhost,127.0.0.1"
```

### Database Options
- SQLite (default): `sqlite:///./app.db`
- PostgreSQL: `postgresql://user:password@localhost/kitsapi`
- MySQL: `mysql+pymysql://user:password@localhost/kitsapi`

---

## 🚨 Troubleshooting

### Issue: Import errors
**Solution**: Ensure all dependencies are installed
```bash
pip install -r requirements.txt --upgrade
```

### Issue: Port already in use
**Solution**: Change port or kill existing process
```bash
python -m uvicorn app.main:app --port 8001
# or
lsof -ti:8000 | xargs kill -9
```

### Issue: FFmpeg not found
**Solution**: Install FFmpeg
```bash
# Ubuntu/Debian
sudo apt-get install ffmpeg

# macOS
brew install ffmpeg

# Windows
# Download from https://ffmpeg.org/download.html
```

### Issue: Tests failing
**Solution**: Check detailed test output
```bash
python -m pytest tests/ -v --tb=short
```

### Issue: Database locked (SQLite)
**Solution**: Delete old database and restart
```bash
rm app.db
python -m uvicorn app.main:app --reload
```

---

## 📚 Documentation

- **API Docs**: http://localhost:8000/docs (Swagger UI)
- **Alternative Docs**: http://localhost:8000/redoc (ReDoc)
- **DEPLOYMENT.md**: Deployment procedures
- **OPTIMIZATION.md**: Performance optimization details
- **PRODUCTION_READY.md**: Production checklist
- **Endpoint Documentation**: [ENDPOINTS.md](ENDPOINTS.md)

---

## 🤝 Contributing

1. Create a new branch: `git checkout -b feature/name`
2. Make your changes
3. Run tests: `pytest tests/ -v`
4. Commit: `git commit -am "feat: description"`
5. Push: `git push origin feature/name`
6. Create Pull Request

---

## ✅ Verification Checklist

Before pushing code:
- [ ] All tests pass: `pytest tests/ -v`
- [ ] No warnings: `pytest tests/ -v 2>&1 | grep -i warning`
- [ ] Code formatted: `black app/`
- [ ] Type checking: `mypy app/ --ignore-missing-imports`
- [ ] Docstrings added
- [ ] No hardcoded secrets
- [ ] No debug prints

---

## 📞 Support

For issues or questions:
1. Check [Troubleshooting](#-troubleshooting) section
2. Review documentation files
3. Check test files for usage examples
4. Review error logs: `docker-compose logs`

---

## 📄 License

See LICENSE file for details.

---

## 🎉 You're Ready!

Your Kits API is now:
- ✅ Installed and configured
- ✅ Tested and verified (100% pass rate)
- ✅ Ready for development
- ✅ Ready for production deployment

Start building amazing file conversion features! 🚀
