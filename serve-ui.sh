#!/bin/bash

# MAARS OS UI Server
# Serves the UI files with a local HTTP server to enable JavaScript

PORT=8080
UI_DIR="services/vessel-interface/public"

echo "🚀 Starting MAARS OS UI Server..."
echo "📁 Serving from: $UI_DIR"
echo "🌐 Server will be available at: http://localhost:$PORT"
echo ""
echo "Available pages:"
echo "  • Home:       http://localhost:$PORT/HOME.html"
echo "  • Canvas:     http://localhost:$PORT/UNIVERSAL_HUB.html"
echo "  • Dashboard:  http://localhost:$PORT/LIVE_DASHBOARD.html"
echo "  • Test:       http://localhost:$PORT/TEST_BUTTONS.html"
echo ""
echo "Press Ctrl+C to stop the server"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Check if Python 3 is available
if command -v python3 &> /dev/null; then
    cd "$UI_DIR" && python3 -m http.server $PORT
elif command -v python &> /dev/null; then
    cd "$UI_DIR" && python -m SimpleHTTPServer $PORT
else
    echo "❌ Error: Python is not installed"
    echo "Please install Python to run the server"
    exit 1
fi

# Made with Bob
