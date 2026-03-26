#!/usr/bin/env bash
set -e
echo "==> Setting up ArchAI dev environment"

echo "--- Frontend ---"
cd frontend && npm install && cd ..

echo "--- Backend ---"
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cd ..

echo "--- Done! ---"
echo "Run: docker-compose up -d"
echo "Then: cd frontend && npm run dev"
echo "And:  cd backend && uvicorn main:app --reload"
