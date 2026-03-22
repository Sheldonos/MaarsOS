#!/bin/bash

# MAARS Universal Hub Launcher
# Launches the Universal Hub interface in the default browser

echo "🚀 Launching MAARS Universal Hub..."
echo ""
echo "📍 Location: services/vessel-interface/public/UNIVERSAL_HUB.html"
echo "🎨 Design System: Void Space (Strict Uncodixfy)"
echo "📦 Features: 15+ Use Case Templates, Drag & Drop Canvas, Real-Time Simulation"
echo ""

# Check if file exists
if [ ! -f "services/vessel-interface/public/UNIVERSAL_HUB.html" ]; then
    echo "❌ Error: UNIVERSAL_HUB.html not found!"
    echo "   Expected location: services/vessel-interface/public/UNIVERSAL_HUB.html"
    exit 1
fi

# Detect OS and open in browser
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    open services/vessel-interface/public/UNIVERSAL_HUB.html
    echo "✅ Universal Hub opened in default browser (macOS)"
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    # Linux
    xdg-open services/vessel-interface/public/UNIVERSAL_HUB.html
    echo "✅ Universal Hub opened in default browser (Linux)"
elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]]; then
    # Windows
    start services/vessel-interface/public/UNIVERSAL_HUB.html
    echo "✅ Universal Hub opened in default browser (Windows)"
else
    echo "⚠️  Could not detect OS. Please open manually:"
    echo "   file://$(pwd)/services/vessel-interface/public/UNIVERSAL_HUB.html"
fi

echo ""
echo "📖 Documentation: services/vessel-interface/UNIVERSAL_HUB_README.md"
echo "🔗 Vision Layer: services/vessel-interface/public/VISION_LAYER.html"
echo ""
echo "💡 Quick Start:"
echo "   1. Expand a domain cluster in the left sidebar"
echo "   2. Drag a use case template onto the canvas"
echo "   3. Click the node to configure parameters"
echo "   4. Click [Run Simulation] to test before deployment"
echo ""
echo "🎯 Phase 8 Preview — Ready for Next.js Migration"

# Made with Bob
