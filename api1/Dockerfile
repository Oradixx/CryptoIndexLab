FROM python:3.12.9-slim-bookworm AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_ROOT_USER_ACTION=ignore \
    VENV_PATH=/opt/venv

WORKDIR /build

RUN python -m venv "${VENV_PATH}"
ENV PATH="${VENV_PATH}/bin:${PATH}"

COPY requirements.txt .
RUN /opt/venv/bin/pip install --upgrade "pip>=25.3" \
    && /opt/venv/bin/pip install --requirement requirements.txt \
    && /opt/venv/bin/pip check

FROM python:3.12.9-slim-bookworm AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    VENV_PATH=/opt/venv \
    PATH="/opt/venv/bin:${PATH}"

WORKDIR /app

RUN apt-get update && apt-get upgrade -y && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 10001 appgroup \
    && useradd --uid 10001 --gid appgroup --home-dir /app --shell /usr/sbin/nologin appuser \
    && chown appuser:appgroup /app

COPY --from=builder /opt/venv /opt/venv

COPY --chown=appuser:appgroup src ./src

USER appuser

EXPOSE 8001

HEALTHCHECK --interval=30s --timeout=3s --start-period=20s --retries=3 \
  CMD python -c "import os, urllib.request; urllib.request.urlopen('http://127.0.0.1:' + os.getenv('PORT', '8001') + '/health', timeout=2)" || exit 1

CMD ["python", "-m", "src.main"]

