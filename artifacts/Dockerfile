ARG BASE_IMAGE=python:3.11-slim
FROM ${BASE_IMAGE}
# To pin to a digest in CI: pass --build-arg BASE_IMAGE='python@sha256:<digest>'
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

LABEL org.opencontainers.image.authors="Elena Konkova"
LABEL org.opencontainers.image.description="AIRI 2026: Learning to Defer Simulation"
LABEL org.opencontainers.image.version="2026.05"

WORKDIR /app
COPY requirements.txt .
RUN pip install --upgrade pip && pip install --no-cache-dir --require-hashes -r requirements.txt
COPY . /app
CMD ["python", "non_oracle_defer_simulation_2026_05.py"]
