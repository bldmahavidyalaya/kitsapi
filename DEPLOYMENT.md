# Kits API - Deployment Guide

## 🚀 Quick Start

### Local Development
```bash
# Clone repository
git clone https://github.com/bldmahavidyalaya/kitsapi.git
cd kitsapi

# Setup virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install system dependencies (optional, for advanced features)
# On Ubuntu/Debian:
sudo apt-get install ffmpeg tesseract-ocr poppler-utils libmagic1

# Run server
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Access:** http://localhost:8000
**API Docs:** http://localhost:8000/docs
**Alternative UI:** http://localhost:8000/redoc

---

## 🐳 Docker Deployment

### Single Container
```bash
docker build -t kitsapi:latest .
docker run -d -p 8000:8000 --name kitsapi kitsapi:latest
```

### Docker Compose (Recommended)
```bash
docker-compose up -d
```

Services:
- Web: `http://localhost:8000`

### Scaling with Docker
```bash
docker-compose up -d --scale web=3  # Run 3 instances
```

---

## ☁️ Cloud Deployment

### AWS EC2 / Ubuntu
```bash
#!/bin/bash
# Update system
sudo apt-get update && sudo apt-get upgrade -y

# Install Python and dependencies
sudo apt-get install -y python3.11 python3-pip
sudo apt-get install -y ffmpeg tesseract-ocr poppler-utils libmagic1

# Clone and setup
git clone https://github.com/bldmahavidyalaya/kitsapi.git
cd kitsapi
pip install -r requirements.txt

# Run with systemd
sudo cp kitsapi.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable kitsapi
sudo systemctl start kitsapi
```

**systemd Service File (`kitsapi.service`):**
```ini
[Unit]
Description=Kits API Service
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/kitsapi
ExecStart=/usr/bin/python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### Heroku
```bash
# Create Procfile
echo "web: uvicorn app.main:app --host 0.0.0.0 --port \$PORT" > Procfile

# Deploy
heroku create kitsapi
git push heroku main
```

### Google Cloud Run
```bash
gcloud run deploy kitsapi \
  --source . \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --port 8000
```

### Railway
```bash
railway link
railway up
```

---

## 🔒 Production Configuration

### Environment Variables
Create `.env` file:
```env
DATABASE_URL=postgresql://user:pass@localhost/kitsapi
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
AWS_S3_BUCKET=your_bucket
LOG_LEVEL=info
API_KEY=your_secret_api_key  # Optional
```

### Nginx Reverse Proxy
```nginx
server {
    listen 80;
    server_name api.example.com;

    client_max_body_size 500M;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeouts for long conversions
        proxy_connect_timeout 600s;
        proxy_send_timeout 600s;
        proxy_read_timeout 600s;
    }
}
```

### SSL/TLS with Let's Encrypt
```bash
sudo apt-get install certbot python3-certbot-nginx
sudo certbot certonly --nginx -d api.example.com
```

### Rate Limiting (Using Nginx)
```nginx
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;

location / {
    limit_req zone=api_limit burst=20 nodelay;
    proxy_pass http://localhost:8000;
}
```

---

## 📊 Performance Optimization

### Gunicorn + Uvicorn (Production)
```bash
pip install gunicorn
gunicorn app.main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

### Scaling Settings
```bash
# 4-core machine: workers = (2 × 4) + 1 = 9
gunicorn app.main:app \
  --workers 9 \
  --worker-class uvicorn.workers.UvicornWorker \
  --worker-connections 1000 \
  --max-requests 10000 \
  --max-requests-jitter 1000 \
  --timeout 120 \
  --bind 0.0.0.0:8000
```

### Load Balancing
```bash
# Using HAProxy
global
    maxconn 4096
    timeout connect 5s
    timeout client 50s
    timeout server 50s

backend api_backend
    balance roundrobin
    server api1 127.0.0.1:8001
    server api2 127.0.0.1:8002
    server api3 127.0.0.1:8003
```

---

## 🗄️ Database Setup

### PostgreSQL (Recommended for Production)
```bash
# Install
sudo apt-get install postgresql postgresql-contrib

# Create database
sudo -u postgres createdb kitsapi
sudo -u postgres createuser kitsapi
sudo -u postgres psql -c "ALTER USER kitsapi WITH PASSWORD 'secure_password';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE kitsapi TO kitsapi;"

# Update .env
DATABASE_URL=postgresql://kitsapi:secure_password@localhost/kitsapi
```

### SQLite (Development/Testing)
```bash
# Already configured, just use:
DATABASE_URL=sqlite:///./kitsapi.db
```

---

## 📈 Monitoring & Logging

### Application Logging
```python
# In app/main.py
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
```

### Using Prometheus + Grafana
```bash
pip install prometheus-client
```

Add to `app/main.py`:
```python
from prometheus_client import Counter, Histogram, make_wsgi_app
from prometheus_client import generate_latest

conversion_counter = Counter('conversions_total', 'Total conversions')
conversion_duration = Histogram('conversion_duration_seconds', 'Conversion time')
```

### CloudWatch (AWS)
```bash
pip install watchtower
```

---

## 🧪 Testing in Production

### Health Checks
```bash
curl http://api.example.com/api/v1/health
# Response: {"status":"ok"}
```

### Load Testing
```bash
pip install locust

# Create locustfile.py
from locust import HttpUser, task, between

class APIUser(HttpUser):
    wait_time = between(1, 3)
    
    @task
    def health_check(self):
        self.client.get("/api/v1/health")

# Run: locust -f locustfile.py --host=http://api.example.com
```

---

## 🔧 Troubleshooting

### Port Already in Use
```bash
lsof -i :8000
kill -9 <PID>
```

### Memory Issues
```bash
# Monitor memory
watch -n 1 'ps aux | grep uvicorn'

# Limit memory usage with Docker
docker run -m 2g kitsapi:latest
```

### Missing Dependencies
```bash
# Check installed packages
pip list

# Reinstall all
pip install -r requirements.txt --force-reinstall
```

---

## 📋 Maintenance

### Database Backups
```bash
# SQLite
cp kitsapi.db kitsapi.db.backup

# PostgreSQL
pg_dump kitsapi > backup.sql
pg_restore -d kitsapi backup.sql
```

### Log Rotation
```bash
# /etc/logrotate.d/kitsapi
/var/log/kitsapi/*.log {
    daily
    rotate 7
    compress
    delaycompress
    notifempty
    create 0640 www-data www-data
}
```

### Automatic Updates
```bash
# Create update script
#!/bin/bash
cd /home/ubuntu/kitsapi
git fetch origin
git reset --hard origin/main
pip install -r requirements.txt
systemctl restart kitsapi
```

---

## 🚨 Security Best Practices

1. **Use HTTPS** - Always use SSL/TLS in production
2. **API Keys** - Implement authentication (JWT/OAuth2)
3. **Rate Limiting** - Prevent abuse with rate limits
4. **CORS** - Configure CORS properly
5. **Input Validation** - Validate all file uploads
6. **File Size Limits** - Set maximum upload sizes
7. **Sandboxing** - Run conversion processes in isolated containers
8. **Secrets Management** - Use environment variables for secrets
9. **Regular Updates** - Keep dependencies updated
10. **Monitoring** - Set up alerts for errors/crashes

---

## 📞 Support

For deployment issues:
- Check logs: `docker logs kitsapi`
- Review API docs: `/docs` endpoint
- Check [ENDPOINTS.md](ENDPOINTS.md) for available conversions
