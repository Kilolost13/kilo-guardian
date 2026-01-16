#!/usr/bin/env bash
set -euo pipefail
# Run Alembic migrations
echo "Running Alembic migrations..."
python3 -m financial.scripts.run_alembic_upgrade || true
echo "Migrations complete, starting uvicorn..."
# Start the service directly without waiting
exec uvicorn main:app --host 0.0.0.0 --port 9005
