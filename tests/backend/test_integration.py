#!/usr/bin/env python3
"""Comprehensive test for FIBO API integrations."""

import os
import sys
import json
import httpx

# Add backend to path
sys.path.append('.')

from app.services.fibo_engine import FIBOEngine, FIBOEngineError
from app.services.bria_client import BriaClient, BriaAPIError
from app.services.vlm_translator import VLMTranslator, VLMTranslatorError
from app.services.environment_validator import EnvironmentValidator


def print_section(title: str):
    """Print a formatted section header."""
    print("\n" + "=" * 50)
    print(f" {title}")
    print("=" * 50)


def test_environment_validation():
    """Test environment validation system."""
    print_section("ENVIRONMENT VALIDATION")
    
    validator = EnvironmentValidator()
    status = validator.validate_environment()
    
    print(f"Overall Status: {status.overall_status.value}")
    print(f"Production Ready: {status.ready_for_production}")
    print()
    
    print("Service Status:")
    for service in status.services:
        icon = "✅" if service.status.value == "available" else "❌" if service.status.value == "unavailable" else "⚠️"
        print(f"  {icon} {service.name}: {service.status.value} - {service.message}")
    
    if status.warnings:
        print(f"\nWarnings: {len(status.warnings)}")
        for warning in status.warnings:
            print(f"  ⚠️ {warning}")
    
    if status.errors:
        print(f"\nErrors: {len(status.errors)}")
        for error in status.errors:
            print(f"  ❌ {error}")
    
    return status


def test_bria_client():
    """Test BRIA client initialization and connection."""
    print_section("BRIA CLIENT")
    
    try:
        client = BriaClient()
        print("✅ BRIA client initialized")
        
        # Try connection test if API key available
        bria_key = os.getenv("BRIA_API_KEY")
        if bria_key and bria_key not in ["", "your_api_key_here", "test_key_for_development"]:
            try:
                client.test_connection()
                print("✅ BRIA API connection successful")
                return True
            except BriaAPIError as e:
                print(f"❌ BRIA API test failed: {e}")
                return False
        else:
            print("⚠️ BRIA API key not configured - skipping connection test")
            return False
            
    except Exception as e:
        print(f"❌ BRIA client error: {e}")
        return False


def test_vlm_translator():
    """Test VLM translator initialization."""
    print_section("VLM TRANSLATOR")
    
    try:
        translator = VLMTranslator()
        print("✅ VLM translator initialized")
        
        # Try a simple translation if API key available
        openai_key = os.getenv("OPENAI_API_KEY")
        if openai_key and openai_key not in ["", "your_openai_api_key_here", "test_key_for_development"]:
            try:
                test_prompt = "simple test"
                result = translator.translate_simple(test_prompt)
                print("✅ VLM translation successful")
                print(f"  Sample result: {result['subject']}")
                return True
            except VLMTranslatorError as e:
                print(f"❌ VLM translation test failed: {e}")
                return False
        else:
            print("⚠️ OpenAI API key not configured - skipping translation test")
            return False
            
    except VLMTranslatorError as e:
        print(f"❌ VLM translator error: {e}")
        return False


def test_fibo_engine():
    """Test FIBO engine initialization and status."""
    print_section("FIBO ENGINE")
    
    try:
        engine = FIBOEngine()
        print("✅ FIBO engine initialized")
        
        status = engine.get_engine_status()
        print(f"Engine Version: {status['version']}")
        print(f"Engine Ready: {status['ready']}")
        
        print("\nFeature Availability:")
        for feature, available in status['features_available'].items():
            icon = "✅" if available else "❌"
            print(f"  {icon} {feature}")
        
        print("\nAPI Status:")
        for api, status_val in status['api_status'].items():
            icon = "✅" if status_val == "configured" else "❌"
            print(f"  {icon} {api}: {status_val}")
        
        if status['missing_requirements']:
            print(f"\nMissing Requirements: {', '.join(status['missing_requirements'])}")
        
        return status['ready']
        
    except Exception as e:
        print(f"❌ FIBO engine error: {e}")
        return False


def test_backend_api():
    """Test backend API health endpoints."""
    print_section("BACKEND API")
    
    try:
        # Test health endpoint
        with httpx.Client(timeout=10.0) as client:
            response = client.get("http://127.0.0.1:8000/api/v1/health")
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Basic health check: {data['status']}")
            else:
                print(f"❌ Health check failed: {response.status_code}")
                return False
            
            # Test detailed health endpoint
            response = client.get("http://127.0.0.1:8000/api/v1/health/detailed")
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Detailed health check: {data['overall_status']}")
                print(f"  Production Ready: {data['ready_for_production']}")
                
                features = data['features_available']
                print("  Feature Availability:")
                for feature, available in features.items():
                    icon = "✅" if available else "❌"
                    print(f"    {icon} {feature}")
                
                return True
            else:
                print(f"❌ Detailed health check failed: {response.status_code}")
                return False
                
    except httpx.ConnectError:
        print("❌ Cannot connect to backend - is it running?")
        print("   Try: cd backend && python -m uvicorn app.main:app --reload")
        return False
    except Exception as e:
        print(f"❌ Backend API test error: {e}")
        return False


def main():
    """Run comprehensive integration tests."""
    print("🔧 FIBO Omni-Director Pro - Integration Test")
    print(f"Python: {sys.version}")
    print(f"Working Directory: {os.getcwd()}")
    
    # Test results
    results = {}
    
    # 1. Environment validation
    env_status = test_environment_validation()
    results['environment'] = env_status.overall_status.value == "available"
    
    # 2. BRIA client
    results['bria_client'] = test_bria_client()
    
    # 3. VLM translator
    results['vlm_translator'] = test_vlm_translator()
    
    # 4. FIBO engine
    results['fibo_engine'] = test_fibo_engine()
    
    # 5. Backend API (if running)
    results['backend_api'] = test_backend_api()
    
    # Summary
    print_section("TEST SUMMARY")
    
    passed = sum(results.values())
    total = len(results)
    
    print(f"Tests Passed: {passed}/{total}")
    
    for test, result in results.items():
        icon = "✅" if result else "❌"
        print(f"  {icon} {test}")
    
    if passed == total:
        print("\n🎉 All tests passed! System is ready for development.")
    else:
        print(f"\n⚠️  {total - passed} tests failed. Check configuration:")
        if not results.get('bria_client'):
            print("  - Set BRIA_API_KEY environment variable")
        if not results.get('vlm_translator'):
            print("  - Set OPENAI_API_KEY environment variable") 
        if not results.get('backend_api'):
            print("  - Start backend server: uvicorn app.main:app --reload")


if __name__ == "__main__":
    main()