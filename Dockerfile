FROM python:3.12-alpine

ENV TS_LEGALCHECK_DEFINITIONS_PATH=/data/definitions

RUN apk add --no-cache build-base

COPY data /data
COPY src /app/src
COPY pyproject.toml /app/

RUN pip install --upgrade pip && \
    pip install /app

RUN rm -rf /app

# Set entrypoint to the CLI tool
ENTRYPOINT ["python", "-m", "ts_legalcheck.cli"]

# Default command
CMD ["--help"]
