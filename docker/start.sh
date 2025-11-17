#!/bin/bash
set -e

# Color output for readability
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}[MyWave] Starting application initialization...${NC}"

# 1. Check database connectivity
echo -e "${YELLOW}[MyWave] Waiting for database connection...${NC}"
max_attempts=30
attempt=0
while [ $attempt -lt $max_attempts ]; do
    if pg_isready -h db -U ${POSTGRES_USER:-mywave_user} -q 2>/dev/null; then
        echo -e "${GREEN}[MyWave] Database is ready!${NC}"
        break
    fi
    attempt=$((attempt + 1))
    echo -e "${YELLOW}[MyWave] Attempt $attempt/$max_attempts: Waiting for database...${NC}"
    sleep 1
done

if [ $attempt -eq $max_attempts ]; then
    echo -e "${RED}[MyWave] ERROR: Database connection failed after $max_attempts attempts${NC}"
    exit 1
fi

# 2. Run database migrations
echo -e "${YELLOW}[MyWave] Running database migrations...${NC}"
if python -c "from app import create_app; app = create_app(); app.app_context().push()" 2>/dev/null; then
    flask db upgrade || {
        echo -e "${YELLOW}[MyWave] No pending migrations or migration check skipped${NC}"
    }
else
    echo -e "${YELLOW}[MyWave] Skipping migrations in standalone container${NC}"
fi

# 3. Check Redis connectivity (if needed for SocketIO)
if [ ! -z "$REDIS_URL" ]; then
    echo -e "${YELLOW}[MyWave] Checking Redis connection...${NC}"
    redis_host=$(echo $REDIS_URL | sed 's|redis://\([^:]*\):.*|\1|')
    redis_port=$(echo $REDIS_URL | sed 's|.*:\([0-9]*\).*|\1|')
    
    redis_attempts=0
    while [ $redis_attempts -lt 10 ]; do
        if nc -z $redis_host $redis_port 2>/dev/null; then
            echo -e "${GREEN}[MyWave] Redis is ready!${NC}"
            break
        fi
        redis_attempts=$((redis_attempts + 1))
        sleep 1
    done
fi

# 4. Create necessary directories
mkdir -p /app/logs /app/uploads /app/cache

echo -e "${GREEN}[MyWave] Starting Gunicorn application server...${NC}"
echo -e "${YELLOW}[MyWave] Configuration:${NC}"
echo "  - Bind address: 0.0.0.0:5000"
echo "  - Workers: 4"
echo "  - Worker class: gevent"
echo "  - Timeout: 120s"
echo "  - Environment: ${FLASK_ENV:-production}"

# 5. Start application with Gunicorn
exec gunicorn \
    --bind 0.0.0.0:5000 \
    --workers 4 \
    --worker-class gevent \
    --timeout 120 \
    --keep-alive 5 \
    --max-requests 1000 \
    --max-requests-jitter 100 \
    --access-logfile - \
    --error-logfile - \
    --log-level info \
    --access-log-format '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s' \
    wsgi:app
