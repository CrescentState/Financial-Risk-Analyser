#!/usr/bin/env python3
"""Run both backend and frontend simultaneously with proper process management."""
import subprocess
import signal
import sys
import time
import os

# Activate venv
os.chdir(os.path.dirname(os.path.abspath(__file__)))
venv_python = os.path.join(os.getcwd(), ".venv", "bin", "python")

processes = []

def cleanup(signum=None, frame=None):
    print("\nShutting down...")
    for p in processes:
        if p.poll() is None:
            p.terminate()
    for p in processes:
        try:
            p.wait(timeout=5)
        except subprocess.TimeoutExpired:
            p.kill()
    print("Done.")
    sys.exit(0)

signal.signal(signal.SIGINT, cleanup)
signal.signal(signal.SIGTERM, cleanup)

print("Starting Chrimatos Financial Risk Analyser...")
print("Backend:  http://localhost:8000")
print("Frontend: http://localhost:8501")
print("API Docs: http://localhost:8000/docs")
print("Press Ctrl+C to stop both services\n")

# Start backend
backend = subprocess.Popen(
    [venv_python, "-m", "uvicorn", "main:app", "--port", "8000"],
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
    bufsize=1,
)
processes.append(backend)

# Wait for backend
print("Waiting for backend...")
for _ in range(30):
    try:
        import urllib.request
        urllib.request.urlopen("http://localhost:8000/health", timeout=2)
        print("Backend ready!")
        break
    except:
        time.sleep(1)
else:
    print("Backend failed to start")
    cleanup()

# Start frontend
frontend = subprocess.Popen(
    [venv_python, "-m", "streamlit", "run", "frontend/app.py", "--server.port", "8501", "--server.headless", "true"],
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
    bufsize=1,
)
processes.append(frontend)

# Stream output
print("\nBoth services running. Logs:\n" + "="*50)
try:
    while True:
        for p in processes:
            line = p.stdout.readline()
            if line:
                print(f"[{p.args[2] if len(p.args)>2 else p.args[0]}] {line.rstrip()}")
        if all(p.poll() is not None for p in processes):
            break
except KeyboardInterrupt:
    pass
finally:
    cleanup()