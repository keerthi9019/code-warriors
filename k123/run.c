#!/usr/bin/env python
"""
FreshKeeper - AI-Powered Food Waste Reduction App
Run script for easier application startup
"""

import os
import sys

def main():
    """Main function to run the FreshKeeper application"""

    print("🌱 Starting FreshKeeper - Food Waste Reduction App")
    print("=" * 50)

    # Check Python version
    if sys.version_info < (3, 8):
        print("❌ Error: Python 3.8 or higher is required")
        print(f"xCurrent version: {sys.version}")
        return False

    # Try to import required modules
    try:
        import flask
        print(f"✅ Flask version: {flask.__version__}")
    except ImportError:
        print("❌ Error: Flask not installed. Run: pip install -r requirements.txt")
        return False

    # Import and run the app
    try:
        from app import app
        print("✅ FreshKeeper loaded successfully")
        print("🌐 Starting web server...")
        print("📱 Access the application at: http://localhost:5000")
        print("🛑 Press Ctrl+C to stop the server")
        print("=" * 50)

        # Run the Flask app
        app.run(debug=True, host='0.0.0.0', port=5000)

    except Exception as e:
        print(f"❌ Error starting application: {e}")
        return False

    return True

if __name__ == "__main__":
    main()
