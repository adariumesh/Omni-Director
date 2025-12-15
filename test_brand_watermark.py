#!/usr/bin/env python3
"""Test brand protection watermarking system."""

import sys
sys.path.append('/Users/adariprasad/weapon/Omni - Director/backend')

from app.services.brand_guard import BrandGuard, BrandGuidelines
from PIL import Image, ImageDraw
import tempfile
import os

def create_test_image():
    """Create a test image for watermarking."""
    img = Image.new('RGB', (800, 600), color='lightblue')
    draw = ImageDraw.Draw(img)
    draw.text((50, 50), "FIBO Test Generation", fill='black')
    draw.rectangle([100, 100, 700, 500], outline='red', width=3)
    
    temp_path = tempfile.mktemp(suffix='.png')
    img.save(temp_path)
    return temp_path

def create_test_logo():
    """Create a simple test logo."""
    logo = Image.new('RGBA', (100, 40), color='white')
    draw = ImageDraw.Draw(logo)
    draw.text((10, 10), "FIBO", fill='blue')
    
    logo_path = '/Users/adariprasad/weapon/Omni - Director/data/fibo_logo.png'
    os.makedirs(os.path.dirname(logo_path), exist_ok=True)
    logo.save(logo_path)
    return logo_path

def test_watermarking():
    """Test the brand protection watermarking."""
    print("🧪 Testing Brand Protection Watermarking...")
    
    # Create test assets
    test_image = create_test_image()
    logo_path = create_test_logo()
    
    # Setup brand guidelines
    guidelines = BrandGuidelines(
        logo_path=logo_path,
        logo_position="bottom_right",
        logo_opacity=0.7,
        watermark_enabled=True,
        copyright_text="© FIBO Omni-Director Pro"
    )
    
    # Initialize brand guard
    guard = BrandGuard(guidelines)
    
    # Test watermarking
    result = guard.protect_asset(test_image, "/Users/adariprasad/weapon/Omni - Director/data/test_protected.png")
    
    print(f"✅ Protection completed: {result.compliant}")
    print(f"📊 Compliance score: {result.score}")
    print(f"🛡️ Protected file: {result.protected_asset_path}")
    
    if result.violations:
        print("⚠️ Violations found:")
        for violation in result.violations:
            print(f"  - {violation.severity}: {violation.message}")
    
    # Cleanup
    os.unlink(test_image)
    
    return result.protected_asset_path

if __name__ == "__main__":
    test_watermarking()