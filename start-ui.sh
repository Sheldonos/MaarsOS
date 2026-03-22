#!/bin/bash

# MAARS Home Page Launcher
# This script opens the MAARS Home Page in your default browser

echo "🚀 Starting MAARS OS..."
echo ""
echo "Opening MAARS Home Page in your default browser..."
echo "URL: file://$(pwd)/services/vessel-interface/public/HOME.html"
echo ""
echo "📝 Quick Start:"
echo "  1. The UI will open in demo mode"
echo "  2. Chat with MAARS to build applications and orchestrate agents"
echo "  3. View live previews in the Canvas panel"
echo "  4. To connect to a live MAARS backend:"
echo "     - Start the backend services (see README.md)"
echo "     - API will auto-connect to http://localhost:8000"
echo "  5. Switch between Canvas, Artistry Live, Render, and Code views"
echo ""

# Detect OS and open browser
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    open "services/vessel-interface/public/HOME.html"
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    # Linux
    xdg-open "services/vessel-interface/public/HOME.html"
elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]]; then
    # Windows
    start "services/vessel-interface/public/HOME.html"
else
    echo "⚠️  Could not detect OS. Please manually open:"
    echo "   services/vessel-interface/public/HOME.html"
fi

echo ""
echo "✅ MAARS Home Page launched successfully!"
echo "   The interface will open in your browser"
echo ""
echo "🎨 Design: Modern dark theme with use case cards"
echo "📊 Features: Use Case Templates, Live Preview, Natural Language Input"
echo ""
echo "💡 Available Interfaces:"
echo "   • HOME.html - Landing page with use case builder"
echo "   • UNIVERSAL_HUB.html - Canvas workflow editor"
echo "   • LIVE_DASHBOARD.html - Real-time orchestration monitor"
echo ""
echo "💡 Tip: You can also open the file directly in your browser:"
echo "   file://$(pwd)/services/vessel-interface/public/HOME.html"
echo ""

# Made with Bob
