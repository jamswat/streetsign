# ---------- builder ----------
FROM python:3.12-alpine AS builder

RUN apk add --no-cache build-base python3-dev

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# ---------- final ----------
FROM python:3.12-alpine

RUN apk add --no-cache imagemagick bash su-exec \
 && adduser -D -h /app streetsign

COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DATABASE_FILE=/data/database.db

WORKDIR /app
COPY . .
RUN chmod +x entrypoint.sh

EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD wget -q -O /dev/null http://127.0.0.1:${PORT:-5000}/ || exit 1

ENTRYPOINT ["./entrypoint.sh"]
