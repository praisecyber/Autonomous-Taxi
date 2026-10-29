# syntax=docker/dockerfile:1
FROM python:3.12-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY pyproject.toml ./
COPY backend ./backend
COPY deploy/probix-accounts.json ./deploy/probix-accounts.json
RUN --mount=type=secret,id=proxy_ca \
    if [ -f /run/secrets/proxy_ca ]; then \
      PIP_CERT=/run/secrets/proxy_ca python -m pip install --no-cache-dir .; \
    else python -m pip install --no-cache-dir .; fi
RUN groupadd --gid 10001 taxi && useradd --uid 10001 --gid taxi --no-create-home taxi \
    && mkdir /data && chown taxi:taxi /data
USER 10001:10001
ENV TAXI_DATA_DIR=/data
EXPOSE 8000
CMD ["python","-m","uvicorn","taxi.api:create_app","--factory","--host","0.0.0.0","--port","8000","--workers","1","--proxy-headers","--forwarded-allow-ips","127.0.0.1"]
