#!/bin/bash

echo "================================================"
echo "  Vulnerability Analysis Web Application"
echo "================================================"
echo ""

# Check if dependencies are installed
if ! python -c "import flask, pandas, openpyxl" 2>/dev/null; then
    echo "📦 Installing dependencies..."
    pip install -r requirements.txt --break-system-packages -q
    echo "✅ Dependencies installed"
    echo ""
fi

# Check if sample data exists
if [ ! -f "sample_vulnerability_data.csv" ]; then
    echo "📊 Generating sample data..."
    python generate_sample_data.py
    echo ""
fi

echo "🚀 Starting the application..."
echo ""
echo "📍 Access the application at: http://localhost:5000"
echo ""
echo "Press Ctrl+C to stop the server"
echo "================================================"
echo ""

python app.py
