#!/usr/bin/env python3
"""Test script for VLM translator functionality."""

import os
import sys
import json

# Add backend to path
sys.path.append('.')

from app.services.vlm_translator import VLMTranslator, VLMTranslatorError

def main():
    """Test VLM translator."""
    print("🤖 Testing VLM Translator...")
    print("=" * 50)
    
    # Show current environment
    openai_key = os.getenv('OPENAI_API_KEY', 'Not set')
    print(f"OPENAI_API_KEY: {openai_key[:20] + '...' if len(openai_key) > 20 else openai_key}")
    print()
    
    try:
        # Initialize translator
        translator = VLMTranslator()
        print("✅ VLM Translator initialized successfully")
        
        # Test translation
        test_prompt = "A professional headshot of a business executive with dramatic lighting"
        
        print(f"🔄 Testing prompt: '{test_prompt}'")
        print()
        
        result = translator.translate_to_advanced_request(test_prompt)
        
        print("📋 Translation Result:")
        print("-" * 30)
        print(f"Subject: {result.subject}")
        print(f"Camera Angle: {result.camera.angle}")
        print(f"Lighting Setup: {result.lighting.setup}")
        print(f"Mood: {result.mood}")
        print()
        
        print("📄 Full JSON:")
        print("-" * 30)
        print(json.dumps(result.dict(), indent=2))
        
    except VLMTranslatorError as e:
        print(f"❌ VLM Translator Error: {e}")
        if "API key" in str(e):
            print("💡 Tip: Set OPENAI_API_KEY environment variable")
        
    except Exception as e:
        print(f"❌ Unexpected Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()