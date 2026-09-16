#!/bin/bash
# Convenient runner for PongAI backend with virtual environment
cd "$(dirname "$0")"
./venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000 --reload
