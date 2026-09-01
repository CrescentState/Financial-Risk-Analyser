#!/bin/bash
# Chrimatos Financial Risk Analyser - Quick Start
# 
# This script shows the commands to run. 
# Due to environment constraints, run these in TWO separate terminals:

set -e

source .venv/bin/activate

echo ""
echo "=========================================="
echo "  Chrimatos Financial Risk Analyser"
echo "=========================================="
echo ""
echo "Run these in TWO separate terminals:"
echo ""
echo "TERMINAL 1 (Backend):"
echo "  python -m uvicorn main:app --port 8000 --reload"
echo ""
echo "TERMINAL 2 (Frontend):"
echo "  streamlit run frontend/app.py --server.port 8501"
echo ""
echo "Then open: http://localhost:8501"
echo "=========================================="
echo ""

# Optionally auto-start if you uncomment below:
# python -m uvicorn main:app --port 8000 &
# sleep 3
# streamlit run frontend/app.py --server.port 8501