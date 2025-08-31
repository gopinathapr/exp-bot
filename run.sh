
# Activate virtual environment
source env/bin/activate

# Check if LocalTunnel is installed, install if missing
if ! command -v lt &> /dev/null; then
    echo "LocalTunnel not found. Installing..."
    npm install -g localtunnel
fi

# Start Uvicorn in the background
uvicorn bot:app --reload --host 0.0.0.0 --port 8080 --env-file config.env &
UVICORN_PID=$!
echo "Uvicorn started with PID $UVICORN_PID"

# Start LocalTunnel with custom subdomain in foreground
lt --port 8080 --subdomain expense-bot-prg

# After LocalTunnel exits, kill Uvicorn
kill $UVICORN_PID