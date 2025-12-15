#!/usr/bin/env python3
"""Test export engine with real data."""

import sys
sys.path.append('/Users/adariprasad/weapon/Omni - Director/backend')

from app.services.export_engine import ExportEngine, ExportAsset, ExportConfig
from app.services.brand_guard import BrandGuard, BrandGuidelines
from datetime import datetime
from PIL import Image, ImageDraw
import tempfile
import os

def create_mock_assets():
    """Create mock assets for testing."""
    assets = []
    
    # Create test images
    for i in range(3):
        # Create test image
        img = Image.new('RGB', (800, 600), color=f'rgb({100 + i * 50}, {150}, {200})')
        draw = ImageDraw.Draw(img)
        draw.text((50, 50), f"FIBO Test Asset {i+1}", fill='white')
        draw.text((50, 100), f"Generated: {datetime.now()}", fill='white')
        
        # Save temporarily
        temp_path = f'/Users/adariprasad/weapon/Omni - Director/data/test_asset_{i+1}.png'
        os.makedirs(os.path.dirname(temp_path), exist_ok=True)
        img.save(temp_path)
        
        # Create asset
        asset = ExportAsset(
            asset_id=f"test_asset_{i+1}",
            image_url=f"https://example.com/image_{i+1}.png",
            prompt=f"A beautiful test image number {i+1} with vibrant colors",
            structured_prompt=f"test, beautiful, image, number-{i+1}, vibrant, colors",
            request_json={
                "prompt": f"A beautiful test image number {i+1}",
                "mode": "fibo",
                "aspect_ratio": "1:1",
                "seed": 42 + i
            },
            metadata={
                "mode": "fibo",
                "generation_time": 2.5,
                "engine": "test"
            },
            seed=42 + i,
            aspect_ratio="1:1",
            created_at=datetime.now(),
            local_path=temp_path
        )
        assets.append(asset)
    
    return assets

def test_portfolio_export():
    """Test portfolio export functionality."""
    print("🧪 Testing Portfolio Export...")
    
    # Create mock assets
    assets = create_mock_assets()
    
    # Configure export with brand protection
    config = ExportConfig(
        include_images=True,
        include_json=True,
        include_csv=True,
        include_metadata=True,
        create_zip=True,
        apply_watermark=True,
        image_format="PNG",
        image_quality=95,
        naming_convention="descriptive"
    )
    
    # Initialize export engine
    engine = ExportEngine("/Users/adariprasad/weapon/Omni - Director/backend/exports")
    
    # Test portfolio export
    result = engine.export_portfolio(assets, config)
    
    print(f"✅ Export Success: {result.success}")
    print(f"📁 Export Path: {result.export_path}")
    print(f"📊 Files Created: {result.file_count}")
    print(f"💾 Total Size: {result.total_size / 1024:.1f} KB")
    print(f"🎯 Assets Exported: {result.assets_exported}/{len(assets)}")
    
    if result.errors:
        print("❌ Errors:")
        for error in result.errors:
            print(f"  - {error}")
    
    if result.warnings:
        print("⚠️ Warnings:")
        for warning in result.warnings:
            print(f"  - {warning}")
    
    return result

def test_archive_export():
    """Test archive export functionality."""
    print("\n🧪 Testing Archive Export...")
    
    assets = create_mock_assets()
    
    config = ExportConfig(
        export_format="archive",
        include_technical=True,
        include_metadata=True,
        create_zip=True
    )
    
    engine = ExportEngine("/Users/adariprasad/weapon/Omni - Director/backend/exports")
    result = engine.export_archive(assets, config)
    
    print(f"✅ Archive Success: {result.success}")
    print(f"📁 Archive Path: {result.export_path}")
    print(f"💾 Archive Size: {result.total_size / 1024:.1f} KB")
    
    return result

def test_with_brand_protection():
    """Test export with brand protection integration."""
    print("\n🧪 Testing Brand Protection Integration...")
    
    # Setup brand guidelines
    guidelines = BrandGuidelines(
        logo_path="/Users/adariprasad/weapon/Omni - Director/data/fibo_logo.png",
        watermark_enabled=True,
        copyright_text="© FIBO Omni-Director Pro"
    )
    
    # Initialize brand guard
    guard = BrandGuard(guidelines)
    
    # Create test asset
    assets = create_mock_assets()[:1]  # Just one asset
    
    # Apply brand protection to asset
    if assets[0].local_path:
        protection_result = guard.protect_asset(
            assets[0].local_path,
            "/Users/adariprasad/weapon/Omni - Director/data/protected_test.png"
        )
        
        print(f"🛡️ Brand Protection: {protection_result.compliant}")
        print(f"📊 Protection Score: {protection_result.score}")
        
        # Update asset to use protected version
        if protection_result.protected_asset_path:
            assets[0].local_path = protection_result.protected_asset_path
    
    # Export with protection
    config = ExportConfig(apply_watermark=False)  # Already protected
    engine = ExportEngine("/Users/adariprasad/weapon/Omni - Director/backend/exports")
    result = engine.export_portfolio(assets, config)
    
    print(f"✅ Protected Export: {result.success}")
    
    return result

if __name__ == "__main__":
    portfolio_result = test_portfolio_export()
    archive_result = test_archive_export()
    protection_result = test_with_brand_protection()
    
    print(f"\n📋 Summary:")
    print(f"Portfolio Export: {'✅' if portfolio_result.success else '❌'}")
    print(f"Archive Export: {'✅' if archive_result.success else '❌'}")
    print(f"Protected Export: {'✅' if protection_result.success else '❌'}")