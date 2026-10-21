FROM python:3.12-slim

ENV TS_LEGALCHECK_MODELS_PATH=/data
ENV TS_LEGALCHECK_DEFINITIONS_PATH=/data/definitions
ENV TS_LEGALCHECK_WEBUI_PORT=5000

COPY src /app/src
COPY pyproject.toml /app/

RUN pip install --upgrade pip && \
    pip install /app

RUN rm -rf /app

COPY data /data

EXPOSE 5000

# Set entrypoint to the CLI tool
ENTRYPOINT ["python", "-m", "ts_legalcheck.cli"]

# Default command
CMD ["start"]
