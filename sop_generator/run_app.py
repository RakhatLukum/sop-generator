#!/usr/bin/env python3
"""
Entrypoint script for SOP Generator deployment
"""

import os
import sys

# Add the current directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

if __name__ == "__main__":
    # Try to import and run the professional app first
    try:
        from app_professional import main
        print("🚀 Starting Professional SOP Generator...")
        main()
    except ImportError as e:
        print(f"⚠️ Could not import professional app: {e}")
        print("🔄 Falling back to basic app...")
        try:
            from app import main
            main()
        except ImportError as e2:
            print(f"❌ Could not import basic app either: {e2}")
            print("Please check your dependencies and try again.")
            sys.exit(1)