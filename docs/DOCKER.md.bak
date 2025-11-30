# Docker Deployment Guide - MyWave Safari Application

## Overview

This guide provides complete instructions for containerizing and deploying the MyWave Safari application using Docker and Docker Compose.

## Architecture

### Services
- **web**: Flask application with Gunicorn WSGI server
- **db**: PostgreSQL 15 database
- **redis**: Redis for caching and SocketIO message queue
- **nginx**: Reverse proxy with SSL/TLS termination

### Key Features
- Multi-stage Docker build for optimized image size
- Health checks on all services
- Non-root user for security
- Prometheus metrics exposure
- Automatic database migrations
- Redis caching and session management
- Nginx rate limiting and security headers
- SSL/TLS with automatic redirect from HTTP

## Prerequisites

- Docker 20.10+ with Docker Compose 2.0+
- Python 3.11 (for local development)
- PostgreSQL 15+ (only if not using Docker)
- At least 2GB RAM and 5GB disk space

## Quick Start

### 1. Prepare Environment

```bash
# Copy and configure environment file
cp .env.docker .env

# Edit .env with your actual values:
# - POSTGRES_PASSWORD
# - SECRET_KEY
# - GOOGLE_SERVICE_ACCOUNT_FILE path
# - OPENAI_API_KEY
# - Email configuration
```

### 2. Initialize Service Account

```bash
# Copy your Google service account JSON to instance directory
cp /path/to/service_account.json ./instance/service_account.json

# Verify permissions
chmod 600 ./instance/service_account.json
```

### 3. Build and Start

```bash
# Build Docker images (one-time)
docker-compose build

# Start all services
docker-compose up -d

# Check service status
docker-compose ps

# View logs
docker-compose logs -f web

# Test health endpoint
curl http://localhost:5000/api/metrics/health
```

### 4. Initialize Database

```bash
# Run migrations inside container
docker-compose exec web flask db upgrade

# Create admin user (if needed)
docker-compose exec web flask create-admin

# Check database
docker-compose exec db psql -U mywave_user -d mywave_safari -c '\dt'
```

## Configuration

### Environment Variables

Key variables in `.env.docker`:

```env
# Database
POSTGRES_USER=mywave_user
POSTGRES_PASSWORD=your_secure_password
POSTGRES_DB=mywave_safari
DATABASE_URL=postgresql://...

# Redis
REDIS_URL=redis://redis:6379/0

# Google Services
GOOGLE_SERVICE_ACCOUNT_FILE=/app/instance/service_account.json
ANALYTICS_SHEET_SPREADSHEET_ID=your_sheet_id
GOOGLE_CALENDAR_ID=your_calendar_id

# OpenAI
OPENAI_API_KEY=sk-...
ASSISTANT_ID=asst_...

# Security
SECRET_KEY=your_very_secret_key
CORS_ORIGINS=http://localhost:3000,https://mywave.com
```

### Docker Compose Override

For local development, create `docker-compose.override.yml`:

```yaml
version: '3.8'

services:
  web:
    environment:
      FLASK_ENV: development
      DEBUG: 'true'
    volumes:
      - .:/app  # Hot reload
    ports:
      - "5000:5000"

  db:
    ports:
      - "5432:5432"
    environment:
      POSTGRES_INITDB_ARGS: "--encoding=UTF8"
```

Then: `docker-compose up` (will merge both files)

## Service Details

### Web Service (Flask App)

**Dockerfile**: Multi-stage build optimizes image size
- Builder stage: Install dependencies into wheels
- Runtime stage: Copy wheels and app, run as non-root user

**Gunicorn Configuration**:
```
Workers: 4
Worker Class: gevent (for async/WebSocket support)
Timeout: 120 seconds
Max Requests: 1000 (worker recycling for memory management)
```

**Health Check**:
```bash
curl http://localhost:5000/api/metrics/health
```

Endpoint response:
```json
{
  "status": "healthy",
  "db": "connected",
  "redis": "connected"
}
```

**Ports**:
- `5000`: Main application (HTTP)
- `5001`: SocketIO (WebSocket) - if enabled
- `9090`: Prometheus metrics (internal)

### Database Service (PostgreSQL)

**Configuration**:
- Image: postgres:15-alpine (lightweight)
- Database: mywave_safari
- User: mywave_user
- Volume: pgdata (persistent storage)

**Initialization**:
Runs `docker/init.sql` automatically on first start:
- Creates extensions (uuid-ossp, pg_trgm)
- Sets up audit schema
- Initializes logging tables

**Backup and Restore**:

```bash
# Backup database
docker-compose exec db pg_dump -U mywave_user mywave_safari > backup.sql

# Restore database
docker-compose exec -T db psql -U mywave_user mywave_safari < backup.sql

# Check size
docker-compose exec db du -sh /var/lib/postgresql/data
```

### Redis Service

**Purpose**:
- Session storage
- Caching (query results, API responses)
- SocketIO message queue
- Rate limiting data

**Health Check**:
```bash
docker-compose exec redis redis-cli ping
# Response: PONG
```

**Monitor Memory**:
```bash
docker-compose exec redis redis-cli info memory
```

### Nginx Service

**Configuration**: `docker/nginx.conf`

**Features**:
- SSL/TLS termination
- Rate limiting (10/s general, 30/s API, 5/m auth)
- Gzip compression
- Security headers
- Static file caching
- Reverse proxy to Flask

**Rate Limiting Zones**:
```
general: 10 req/s per IP (20 burst)
api: 30 req/s per IP (50 burst)
auth: 5 req/min per IP (5 burst)
```

## Common Tasks

### View Logs

```bash
# All services
docker-compose logs

# Specific service (follow output)
docker-compose logs -f web

# Last 100 lines
docker-compose logs --tail=100 web

# Timestamp format
docker-compose logs --timestamps web
```

### Database Operations

```bash
# Connect to database
docker-compose exec db psql -U mywave_user -d mywave_safari

# Run SQL file
docker-compose exec db psql -U mywave_user -d mywave_safari -f script.sql

# Create backup
docker-compose exec db pg_dump -U mywave_user mywave_safari | gzip > backup_$(date +%Y%m%d_%H%M%S).sql.gz

# Check connections
docker-compose exec db psql -U mywave_user -d mywave_safari -c 'SELECT datname, count(*) FROM pg_stat_activity GROUP BY datname;'
```

### Check Metrics

```bash
# Health status
curl http://localhost:5000/api/metrics/health

# Prometheus metrics
curl http://localhost:9090/metrics

# API request metrics
curl -H "Authorization: Bearer <token>" http://localhost:5000/api/metrics/stats
```

### Clear Cache

```bash
# Flush all Redis data
docker-compose exec redis redis-cli FLUSHALL

# Flush specific database
docker-compose exec redis redis-cli -n 0 FLUSHDB
```

## Troubleshooting

### Application fails to start

```bash
# Check logs
docker-compose logs web

# Common issues:
# - Database not ready: Check db service health
# - Missing environment variable: Check .env file
# - Port already in use: Change port in docker-compose.yml

# Rebuild and restart
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### Database connection errors

```bash
# Check database health
docker-compose exec db pg_isready

# Verify credentials
docker-compose exec db psql -U mywave_user -d mywave_safari -c 'SELECT 1;'

# Reset database (WARNING: deletes all data)
docker-compose down -v
docker-compose up -d db
docker-compose exec web flask db upgrade
```

### Performance issues

```bash
# Check resource usage
docker stats

# Check database connections
docker-compose exec db psql -U mywave_user -d mywave_safari -c 'SELECT pid, usename, state FROM pg_stat_activity;'

# Check Redis memory
docker-compose exec redis redis-cli info memory

# Check slow queries
docker-compose logs web | grep "slow"
```

### SSL/TLS issues

```bash
# Generate self-signed certificate (testing only)
mkdir -p docker/ssl
openssl req -x509 -newkey rsa:4096 -keyout docker/ssl/key.pem -out docker/ssl/cert.pem -days 365 -nodes

# For production, use Let's Encrypt with Certbot:
certbot certonly --webroot -w ./docker -d yourdomain.com
cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem docker/ssl/cert.pem
cp /etc/letsencrypt/live/yourdomain.com/privkey.pem docker/ssl/key.pem
```

## Production Deployment

### Best Practices

1. **Secrets Management**
   - Use Docker secrets or environment variables
   - Never commit `.env` to git
   - Rotate API keys regularly

2. **Resource Limits**
   ```yaml
   services:
     web:
       deploy:
         resources:
           limits:
             cpus: '2'
             memory: 2G
           reservations:
             cpus: '1'
             memory: 1G
   ```

3. **Health Checks**
   - All services have health checks
   - Docker will restart unhealthy containers
   - Monitor health check status: `docker-compose ps`

4. **Logging**
   - Configure log rotation in docker-compose.yml
   - Use Docker log drivers (json-file, syslog, etc.)
   - Centralize logs with ELK or similar

5. **Updates**
   ```bash
   # Update Docker images
   docker-compose pull
   docker-compose up -d
   
   # Migrate database (if needed)
   docker-compose exec web flask db upgrade
   ```

### Scaling

For high load, consider:

```yaml
# docker-compose.prod.yml
services:
  web:
    deploy:
      replicas: 3  # Run multiple instances
      update_config:
        parallelism: 1
        delay: 10s
```

Then: `docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d`

## Cleanup

```bash
# Stop services (keep data)
docker-compose stop

# Remove containers
docker-compose down

# Remove everything including volumes (WARNING: deletes all data)
docker-compose down -v

# Remove unused images
docker image prune

# Remove all unused Docker resources
docker system prune -a
```

## Monitoring

### Health Checks

```bash
# Check all services
docker-compose ps

# Manual health check
docker-compose exec web curl -s http://localhost:5000/api/metrics/health | jq
```

### Prometheus Integration

If using Prometheus for monitoring:

```yaml
# prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'mywave'
    static_configs:
      - targets: ['localhost:9090']
```

Start Prometheus: `docker run -p 9090:9090 -v $(pwd)/prometheus.yml:/etc/prometheus/prometheus.yml prom/prometheus`

Then access: `http://localhost:9090`

## Support

For issues or questions:
- Check logs: `docker-compose logs -f web`
- Verify .env configuration
- Test database connectivity: `docker-compose exec db psql -U mywave_user`
- Review Docker documentation: https://docs.docker.com

## Additional Resources

- Docker Documentation: https://docs.docker.com
- Flask Docker Guide: https://flask.palletsprojects.com/en/latest/deploying/docker/
- PostgreSQL Docker: https://hub.docker.com/_/postgres
- Nginx Configuration: https://nginx.org/en/docs/
