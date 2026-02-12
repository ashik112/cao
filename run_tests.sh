#!/bin/bash
set -e

echo "Building test image..."
docker build -t cao-tests .

echo "Running tests..."
docker run --rm -v $(pwd):/app -e PYTHONPATH=/app cao-tests pytest -v
