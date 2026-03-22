#!/bin/bash

# MAARS Live Dashboard Launcher
# Launches the Live Orchestration Dashboard in the default browser

echo "🚀 Launching MAARS Live Dashboard..."
echo ""
echo "📍 Location: services/vessel-interface/public/LIVE_DASHBOARD.html"
echo "🎨 Design: Real-time orchestration monitoring interface"
echo "📊 Features: Live Swarm Roster, Orchestration Canvas, Mission Intel, Performance Metrics"
echo ""

# Check if file exists
if [ ! -f "services/vessel-interface/public/LIVE_DASHBOARD.html" ]; then
    echo "❌ Error: LIVE_DASHBOARD.html not found!"
    echo "   Expected location: services/vessel-interface/public/LIVE_DASHBOARD.html"
    exit 1
fi

# Detect OS and open in browser
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    open services/vessel-interface/public/LIVE_DASHBOARD.html
    echo "✅ Live Dashboard opened in default browser (macOS)"
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    # Linux
    xdg-open services/vessel-interface/public/LIVE_DASHBOARD.html
    echo "✅ Live Dashboard opened in default browser (Linux)"
elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]]; then
    # Windows
    start services/vessel-interface/public/LIVE_DASHBOARD.html
    echo "✅ Live Dashboard opened in default browser (Windows)"
else
    echo "⚠️  Could not detect OS. Please open manually:"
    echo "   file://$(pwd)/services/vessel-interface/public/LIVE_DASHBOARD.html"
fi

echo ""
echo "📖 Interface Overview:"
echo "   • Left Nav: Quick access to all MAARS modules"
echo "   • Swarm Roster: Live status of all running workflows"
echo "   • Center Canvas: Real-time orchestration visualization"
echo "   • Mission Intel: Output stream, performance, and action items"
echo ""
echo "💡 Quick Actions:"
echo "   • Click swarm cards to view details"
echo "   • Monitor agent execution in real-time"
echo "   • Approve/defer pending actions"
echo "   • Use Pause All to halt all workflows"
echo ""
echo "🎯 Real-Time Monitoring — Production Ready"

# Made with Bob