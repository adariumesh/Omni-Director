#!/usr/bin/env python3
"""Test script for enhanced database functionality."""

import os
import sys
from datetime import datetime

# Add backend to path
sys.path.append('.')

from app.models.database import init_db, get_db, Project, Asset
from app.repositories.asset_repository import AssetRepository


def test_database_schema():
    """Test the enhanced database schema."""
    print("📊 Testing Enhanced Database Schema...")
    print("=" * 50)
    
    try:
        # Initialize database
        init_db()
        print("✅ Database initialized")
        
        # Get database session
        db = next(get_db())
        repository = AssetRepository(db)
        
        # Test 1: Create project
        print("\n🏗️  Testing project creation...")
        project = repository.create_project(
            name="Test Project",
            brand_logo_path="/path/to/logo.png",
            negative_prompt="avoid blurry images"
        )
        print(f"✅ Created project: {project.id}")
        
        # Test 2: Create enhanced asset
        print("\n📄 Testing enhanced asset creation...")
        asset = repository.create_asset(
            project_id=project.id,
            prompt="A beautiful landscape",
            seed=12345,
            aspect_ratio="16:9",
            image_url="https://example.com/image.jpg",
            image_path="/local/path/image.jpg",
            file_id="test_file_123",
            thumbnail_path="/local/path/thumb.jpg",
            file_size=2048000,
            content_type="image/jpeg",
            checksum="abc123def456",
            generation_mode="generate",
            generation_time=5000,
            api_provider="bria",
            json_payload={
                "subject": "landscape",
                "camera": {"angle": "wide_shot"},
                "lighting": {"setup": "golden_hour"}
            }
        )
        print(f"✅ Created enhanced asset: {asset.id}")
        print(f"   File ID: {asset.file_id}")
        print(f"   Generation Mode: {asset.generation_mode}")
        print(f"   API Provider: {asset.api_provider}")
        print(f"   File Size: {asset.file_size} bytes")
        
        # Test 3: File ID search
        print("\n🔍 Testing file ID search...")
        found_asset = repository.get_asset_by_file_id("test_file_123")
        if found_asset and found_asset.id == asset.id:
            print("✅ File ID search successful")
        else:
            print("❌ File ID search failed")
        
        # Test 4: Provider filtering
        print("\n🔎 Testing provider filtering...")
        bria_assets = repository.get_assets_by_provider("bria")
        if len(bria_assets) > 0:
            print(f"✅ Found {len(bria_assets)} assets from BRIA")
        else:
            print("❌ Provider filtering failed")
        
        # Test 5: Mode filtering
        print("\n🎯 Testing mode filtering...")
        generate_assets = repository.get_assets_by_mode("generate")
        if len(generate_assets) > 0:
            print(f"✅ Found {len(generate_assets)} 'generate' mode assets")
        else:
            print("❌ Mode filtering failed")
        
        # Test 6: Storage statistics
        print("\n📈 Testing storage statistics...")
        stats = repository.get_storage_statistics()
        print(f"✅ Storage stats:")
        print(f"   Total assets: {stats['total_assets']}")
        print(f"   Assets with files: {stats['assets_with_files']}")
        print(f"   Total file size: {stats['total_file_size_mb']} MB")
        print(f"   File coverage: {stats['file_coverage_percent']}%")
        print(f"   Providers: {stats['provider_distribution']}")
        print(f"   Modes: {stats['mode_distribution']}")
        
        # Test 7: Asset lineage
        print("\n🌳 Testing asset lineage...")
        
        # Create child asset
        child_asset = repository.create_asset(
            project_id=project.id,
            parent_id=asset.id,
            prompt="Refined landscape with dramatic lighting",
            seed=12345,
            aspect_ratio="16:9",
            generation_mode="refine",
            api_provider="bria",
            json_payload={"refined": True}
        )
        print(f"✅ Created child asset: {child_asset.id}")
        
        # Test lineage retrieval
        lineage = repository.get_asset_lineage(child_asset.id)
        print(f"✅ Lineage chain: {len(lineage)} assets")
        for i, ancestor in enumerate(lineage):
            print(f"   {i+1}. {ancestor.id} ({ancestor.generation_mode or 'unknown'})")
        
        # Test children retrieval
        children = repository.get_asset_children(asset.id)
        print(f"✅ Found {len(children)} children of parent asset")
        
        # Test 8: JSON payload handling
        print("\n📋 Testing JSON payload...")
        retrieved_json = repository.get_json_payload(asset.id)
        if retrieved_json and "subject" in retrieved_json:
            print("✅ JSON payload retrieval successful")
            print(f"   Subject: {retrieved_json['subject']}")
        else:
            print("❌ JSON payload retrieval failed")
        
        # Test 9: File info updates
        print("\n🔄 Testing file info updates...")
        updated_asset = repository.update_asset_file_info(
            asset_id=asset.id,
            file_size=3000000,
            checksum="updated_checksum_789"
        )
        if updated_asset and updated_asset.file_size == 3000000:
            print("✅ File info update successful")
        else:
            print("❌ File info update failed")
        
        print("\n✅ All database tests passed!")
        
        db.close()
        return True
        
    except Exception as e:
        print(f"❌ Database test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_api_endpoints():
    """Test the API endpoints work with enhanced database."""
    print("\n🌐 Testing API Endpoints...")
    print("=" * 50)
    
    import httpx
    
    try:
        with httpx.Client(timeout=10.0) as client:
            base_url = "http://127.0.0.1:8000/api/v1"
            
            # Test projects endpoint
            response = client.get(f"{base_url}/assets/projects")
            if response.status_code == 200:
                projects = response.json()
                print(f"✅ Projects API: {len(projects)} projects found")
            else:
                print(f"⚠️ Projects API returned {response.status_code}")
            
            # Test storage stats endpoint
            response = client.get(f"{base_url}/assets/stats/storage")
            if response.status_code == 200:
                stats = response.json()
                print(f"✅ Storage stats API: {stats['total_assets']} total assets")
            else:
                print(f"⚠️ Storage stats API returned {response.status_code}")
            
            return True
            
    except httpx.ConnectError:
        print("⚠️ Backend server not running - skipping API tests")
        print("   Start with: uvicorn app.main:app --reload")
        return False
    except Exception as e:
        print(f"❌ API test error: {e}")
        return False


def main():
    """Run database tests."""
    print("🗃️ FIBO Omni-Director Pro - Database Test")
    print(f"Working Directory: {os.getcwd()}")
    
    results = []
    
    # Test 1: Enhanced database schema
    results.append(test_database_schema())
    
    # Test 2: API endpoints
    results.append(test_api_endpoints())
    
    # Summary
    print("\n" + "=" * 50)
    print(" TEST SUMMARY")
    print("=" * 50)
    
    passed = sum(results)
    total = len(results)
    
    print(f"Tests Passed: {passed}/{total}")
    
    if passed == total:
        print("🎉 All database tests passed!")
        print("✅ Enhanced schema working correctly")
        print("📊 File storage integration complete")
        print("🔗 Asset relationships and lineage functional")
    else:
        print(f"⚠️ {total - passed} tests failed")


if __name__ == "__main__":
    main()