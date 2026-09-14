#!/usr/bin/env bash
set -e

echo "=== Starting shopping-analyzer container ==="

# Function to handle graceful shutdown
shutdown() {
    echo "[Entrypoint] Received termination signal. Stopping services..."
    if [ -n "$SCHEDULER_PID" ]; then
        kill -TERM "$SCHEDULER_PID" 2>/dev/null || true
    fi
    if [ -n "$STREAMLIT_PID" ]; then
        kill -TERM "$STREAMLIT_PID" 2>/dev/null || true
    fi
    wait 2>/dev/null || true
    echo "[Entrypoint] All services stopped."
    exit 0
}

trap shutdown SIGINT SIGTERM

# Start background scheduler
echo "[Entrypoint] Launching background scheduler.py..."
python scheduler.py &
SCHEDULER_PID=$!

# Start Streamlit dashboard
echo "[Entrypoint] Launching Streamlit dashboard on port 8501..."
streamlit run dashboard.py --server.port=8501 --server.address=0.0.0.0 --server.baseUrlPath=/shopping-analyzer &
STREAMLIT_PID=$!

# Wait for either process to terminate
wait -n "$STREAMLIT_PID" "$SCHEDULER_PID"
shutdown
