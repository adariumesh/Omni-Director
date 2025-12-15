#!/usr/bin/env python3
"""Test script for BRIA API research functionality."""

import os
import sys

# Add backend to path
sys.path.append('.')

from app.services.bria_api_research import research_and_document_bria_api

def main():
    """Run BRIA API research test."""
    print("🔍 Testing BRIA API Research System...")
    print("=" * 50)
    
    # Show current environment
    print(f"BRIA_API_KEY: {os.getenv('BRIA_API_KEY', 'Not set')}")
    print(f"Current working directory: {os.getcwd()}")
    print()
    
    # Run the research
    try:
        result = research_and_document_bria_api()
        print("📋 Research Results:")
        print("-" * 30)
        print(result)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()