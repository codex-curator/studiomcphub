FROM python:3.11-slim

WORKDIR /app

RUN groupadd -r appuser && useradd -r -g appuser -d /app appuser

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download U2-Net model for rembg (avoid cold-start download)
# Model downloads to ~/.u2net/ — do this before switching to appuser
RUN python -c "from rembg import new_session; new_session('u2net')" || true
RUN mkdir -p /home/appuser && cp -r /root/.u2net /home/appuser/.u2net 2>/dev/null || true

COPY . .

RUN chown -R appuser:appuser /app /home/appuser

USER appuser

ENV PORT=8080
ENV HOST=0.0.0.0
ENV PYTHONUNBUFFERED=1

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health')" || exit 1

CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "2", "--threads", "4", "--timeout", "300", "src.mcp_server.server:app"]
