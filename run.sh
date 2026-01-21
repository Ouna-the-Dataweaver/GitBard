#!/bin/bash

# GitLab AI Code Reviewer - Startup Script

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=========================================="
echo "GitLab AI Code Reviewer"
echo "=========================================="

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    uv venv
fi

# Activate virtual environment
source .venv/bin/activate

# Check for .env file
if [ ! -f ".env" ]; then
    echo "Warning: .env file not found!"
    echo "Creating from template..."
    cp .env.example .env
    echo "Please edit .env with your GitLab credentials!"
    exit 1
fi

# Export variables from .env
export $(cat .env | grep -v '^#' | xargs)
export HOST="${HOST:-0.0.0.0}"
export PORT="${PORT:-8585}"

# Check for required environment variables
if [ -z "$GITLAB_PAT" ]; then
    echo "Warning: GITLAB_PAT not set in .env!"
    echo "Please add your GitLab Personal Access Token to .env"
    exit 1
fi

echo "Starting server on ${HOST}:${PORT}..."
echo "Press Ctrl+C to stop"
echo "=========================================="

exec uvicorn app:app --host "${HOST}" --port "${PORT}" --reload
