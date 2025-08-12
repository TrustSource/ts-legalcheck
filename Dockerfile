FROM python:3.12-alpine

# Set workdir
WORKDIR /app

# Install build dependencies
RUN apk add --no-cache build-base

# Copy project files
COPY . /app
# Copy data folder separately to ensure it's available for CLI usage
COPY data /app/data

# Install project (prefer editable if pyproject.toml exists)
RUN pip install --upgrade pip && \
    pip install .

# Set entrypoint to the CLI tool
ENTRYPOINT ["python", "-m", "ts_legalcheck.cli"]

# Default command
CMD ["--help"]
