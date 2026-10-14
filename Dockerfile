# Sathi: the web app and the API in one container. Sandbox only: no real money moves.
#   docker build -t sathi . && docker run -p 8000:8000 -e DEEPSEEK_API_KEY=... sathi
# Secrets come from the host's environment settings, never from the image (.env files are not copied).

FROM node:22-slim AS web
WORKDIR /mobile
COPY mobile/package.json mobile/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY mobile/ ./
# The API is served from the same address under /api.
ENV EXPO_PUBLIC_API_URL=/api
RUN npx expo export --platform web --output-dir dist

FROM python:3.12-slim
WORKDIR /srv/backend
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ ./
COPY --from=web /mobile/dist /srv/web
ENV SATHI_WEB_DIR=/srv/web \
    SATHI_FX_MODE=live \
    WHATSAPP_MODE=off \
    SATHI_LLM_DAILY_CALLS=600 \
    PYTHONUNBUFFERED=1
RUN useradd --create-home sathi && mkdir -p var/audit && chown -R sathi var
USER sathi
EXPOSE 8000
CMD ["sh", "-c", "exec uvicorn app.web:site --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips='*'"]
