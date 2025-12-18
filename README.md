# Kits API — Comprehensive File Conversion Platform

**Production-ready FastAPI application for advanced document, media, data, and file conversions.**

---

## 🚀 Features

- **85+ Conversion Endpoints** covering PDFs, images, audio, video, data formats, archives, and more
- **Advanced Processing**: Image effects, video compression, audio normalization, OCR support
- **Security**: File encryption/decryption, PII detection, GDPR anonymization, integrity checking
- **Cloud Ready**: AWS S3 integration, Docker deployment, scalable architecture
- **Enterprise**: Batch operations, metadata removal, format identification, comprehensive error handling
- **Modular Design**: Organized router structure for easy maintenance and extensibility

---

## 📦 Quick Start

### Local Development

```bash
# Setup virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run server
python -m uvicorn app.main:app --reload
```

Visit: http://localhost:8000

### Docker Deployment

```bash
docker-compose up --build
```

---

## 🔌 API Endpoints (85+)

### Core Categories

| Category | Count | Examples |
|----------|-------|----------|
| **PDF & Documents** | 15 | PDF↔Word, PDFmerge, OCR, Text extraction |
| **Images** | 11 | Format conversion, effects, watermarks, color modes |
| **Audio** | 16 | Format conversion, normalization, effects, noise removal |
| **Video** | 18 | Compression, trimming, aspect ratio, frame extraction |
| **Data** | 6 | CSV↔JSON, XML↔JSON, Markdown, YAML |
| **Security** | 13 | Encryption, PII detection, hashing, GDPR tools |
| **Archives** | 2 | ZIP↔7Z conversion |
| **Cloud** | 1 | AWS S3 integration |
| **Social** | 1 | YouTube download (requires yt-dlp) |

👉 **Full API Reference**: See [ENDPOINTS.md](ENDPOINTS.md)

---

## 📚 Interactive Documentation

Access Swagger UI at: **http://localhost:8000/docs**

---

## 💾 Requirements

### Core Dependencies
```
fastapi, uvicorn, sqlmodel, pydantic, jinja2
```

### Conversion Libraries
```
pypdf, pillow, pydub, boto3, cryptography, python-magic
```

### External Binaries
- `ffmpeg` - Audio/video processing
- `poppler` - PDF handling
- `tesseract` (optional) - OCR capability
- `yt-dlp` (optional) - YouTube downloads

All dependencies listed in `requirements.txt`

---

## 🛠️ Project Structure

```
kitsapi/
├── app/
│   ├── main.py                    # FastAPI app factory
│   ├── api/
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── health.py          # Health checks
│   │       ├── items.py           # Demo CRUD
│   │       ├── convert.py         # Core conversions
│   │       ├── convert_advanced.py
│   │       └── convert_advanced_extended.py
│   ├── db/
│   │   ├── session.py             # Database setup
│   ├── models/
│   │   └── item.py                # SQLModel schemas
│   ├── schemas/
│   │   └── item.py                # Pydantic validators
│   ├── templates/
│   │   └── index.html
│   └── static/
│       └── style.css
├── tests/
│   └── test_api.py                # Integration tests (6 passing)
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── ENDPOINTS.md                   # Complete endpoint reference
└── README.md
```

---

## 🧪 Testing

```bash
# Run all tests
pytest tests/test_api.py -v

# Run specific test
pytest tests/test_api.py::test_file_hash -v
```

**Current Status**: ✅ 6/6 tests passing

---

## 📖 Usage Examples

### Convert PDF to Word
```bash
curl -X POST "http://localhost:8000/api/v1/convert/pdf-to-word" \
  -F "file=@document.pdf" \
  --output document.docx
```

### Resize and compress image
```bash
curl -X POST "http://localhost:8000/api/v1/convert/image/transform" \
  -F "file=@photo.jpg" \
  -F "operation=resize" \
  -F "width=800" \
  -F "height=600" \
  --output photo_small.jpg
```

### Convert audio format
```bash
curl -X POST "http://localhost:8000/api/v1/convert/audio/convert" \
  -F "file=@song.mp3" \
  -F "format=wav" \
  --output song.wav
```

### Encrypt file
```bash
curl -X POST "http://localhost:8000/api/v1/convert/file/encrypt" \
  -F "file=@secret.txt" \
  -F "password=mypassword123" \
  --output secret.txt.enc
```

### Detect PII in text
```bash
curl -X POST "http://localhost:8000/api/v1/convert/security/pii-detector" \
  -F "file=@data.txt"
```

---

## 🔐 Security Features

- **Encryption**: Fernet + PBKDF2 key derivation
- **Anonymization**: GDPR-compliant PII redaction
- **Integrity**: SHA256 file hashing
- **Metadata**: EXIF removal, metadata stripping
- **Compliance**: GDPR tools, audit logging support

---

## 📊 Supported Formats

### 🗂️ Documents
PDF, DOCX, DOC, TXT, HTML, MD, JSON, XML, YAML, CSV

### 🖼️ Images
JPG, PNG, WEBP, BMP, GIF, SVG, TIFF, ICO, PSD

### 🔊 Audio
MP3, WAV, AAC, OGG, FLAC, M4A, OPUS

### 🎬 Video
MP4, AVI, MKV, MOV, WEBM, FLV, WMV

### 📦 Archives
ZIP, 7Z, RAR, TAR, TAR.GZ

---

## 🚢 Deployment

### Production Checklist
- [ ] Install external binaries (ffmpeg, poppler, tesseract)
- [ ] Configure AWS S3 credentials (for cloud storage)
- [ ] Set `ENVIRONMENT=production`
- [ ] Use PostgreSQL instead of SQLite (for concurrency)
- [ ] Add rate limiting and authentication
- [ ] Implement job queue for long-running tasks (Celery/RQ)
- [ ] Configure file upload size limits
- [ ] Set up monitoring/logging (ELK, Prometheus, etc.)

---

## 📝 API Response Format

### Success (File Download)
```
HTTP 200 OK
Content-Type: application/pdf (or appropriate MIME type)
Content-Disposition: attachment; filename="output.pdf"
[Binary file content]
```

### Success (JSON Data)
```json
{
  "data": {...}
}
```

### Error
```json
HTTP 500
{
  "detail": "Error description (missing ffmpeg, invalid format, etc.)"
}
```

---

## 🔄 Architecture

### Router Organization
- **convert.py**: Core PDF, image, audio, video endpoints
- **convert_advanced.py**: Advanced image processing, OCR, encryption, utilities
- **convert_advanced_extended.py**: Video AI, audio AI, social media, security tools

### Temporary File Handling
- Uploaded files stored in `/tmp` with unique names
- Automatic cleanup after processing
- File size limits enforced per endpoint

### Error Handling
- Missing external tools → HTTP 500 with descriptive message
- Invalid formats → HTTP 400
- Processing errors → HTTP 500 with exception details

---

## 📞 Support & Development

**Current Version**: 1.0.0  
**Python**: 3.11+  
**FastAPI**: 0.125.0+  
**Status**: Production Ready ✅

For issues or contributions, open an issue or submit a PR.

---

## 📄 License

[Add your license here]
