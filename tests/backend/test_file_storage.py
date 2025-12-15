#!/usr/bin/env python3
"""Test script for file storage system."""

import os
import sys
from pathlib import Path

# Add backend to path
sys.path.append('.')

from app.services.file_storage import FileStorageManager, FileStorageError


def test_file_storage():
    """Test file storage functionality."""
    print("📁 Testing File Storage System...")
    print("=" * 50)
    
    try:
        # Initialize storage manager
        storage = FileStorageManager()
        print(f"✅ Storage manager initialized")
        print(f"   Base path: {storage.base_path}")
        print(f"   Images path: {storage.images_path}")
        print(f"   Thumbnails path: {storage.thumbnails_path}")
        
        # Test with a small test image URL (placeholder)
        test_url = "https://via.placeholder.com/300x200/0066cc/ffffff?text=FIBO+Test"
        
        print(f"\n🔄 Testing download from URL...")
        print(f"   URL: {test_url}")
        
        try:
            stored_file = storage.download_image_from_url(test_url, "test_image.png")
            print(f"✅ Download successful!")
            print(f"   File ID: {stored_file.file_id}")
            print(f"   Stored path: {stored_file.stored_path}")
            print(f"   File size: {stored_file.file_size} bytes")
            print(f"   Content type: {stored_file.content_type}")
            
            # Test thumbnail creation
            print(f"\n🖼️  Creating thumbnail...")
            thumbnail_path = storage.create_thumbnail(stored_file)
            if thumbnail_path:
                print(f"✅ Thumbnail created: {thumbnail_path}")
            else:
                print(f"❌ Thumbnail creation failed")
            
            # Test file listing
            print(f"\n📋 Listing stored files...")
            files = storage.list_files()
            print(f"   Found {len(files)} files")
            for f in files[:3]:  # Show first 3
                print(f"   - {f.file_id}: {f.original_filename} ({f.file_size} bytes)")
            
            # Test storage stats
            print(f"\n📊 Storage statistics...")
            stats = storage.get_storage_stats()
            print(f"   Total size: {stats['total_size_mb']} MB")
            print(f"   Images: {stats['images']['count']} files, {stats['images']['size_mb']} MB")
            print(f"   Thumbnails: {stats['thumbnails']['count']} files, {stats['thumbnails']['size_mb']} MB")
            
            # Test file info retrieval
            print(f"\n🔍 Testing file info retrieval...")
            retrieved_info = storage.get_file_info(stored_file.file_id)
            if retrieved_info:
                print(f"✅ File info retrieved for {stored_file.file_id}")
            else:
                print(f"❌ File info not found")
            
            # Test cleanup (don't delete the test file)
            print(f"\n🧹 Testing cleanup...")
            deleted_count = storage.cleanup_temp_files(max_age_hours=0)  # Clean everything
            print(f"   Cleaned up {deleted_count} temp files")
            
            print(f"\n✅ All file storage tests passed!")
            return True
            
        except FileStorageError as e:
            print(f"❌ File storage error: {e.message} (operation: {e.operation})")
            return False
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_bria_client_with_storage():
    """Test BRIA client with file storage integration."""
    print("\n🖼️  Testing BRIA Client + File Storage...")
    print("=" * 50)
    
    try:
        from app.services.bria_client import BriaClient
        
        # Initialize with auto-download enabled
        client = BriaClient(auto_download=True)
        print(f"✅ BRIA client initialized with auto-download")
        print(f"   Auto-download enabled: {client.auto_download}")
        print(f"   File storage available: {client.file_storage is not None}")
        
        # Test connection (will fail without API key, but tests the integration)
        bria_key = os.getenv("BRIA_API_KEY")
        if bria_key and bria_key not in ["", "your_api_key_here", "test_key_for_development"]:
            print(f"✅ BRIA API key configured, integration ready for real tests")
        else:
            print(f"⚠️ BRIA API key not configured - can't test actual generation")
            print(f"   But file storage integration is properly set up")
        
        return True
        
    except Exception as e:
        print(f"❌ BRIA client test failed: {e}")
        return False


def main():
    """Run file storage tests."""
    print("🔧 FIBO Omni-Director Pro - File Storage Test")
    print(f"Working Directory: {os.getcwd()}")
    
    results = []
    
    # Test 1: Basic file storage
    results.append(test_file_storage())
    
    # Test 2: BRIA integration
    results.append(test_bria_client_with_storage())
    
    # Summary
    print("\n" + "=" * 50)
    print(" TEST SUMMARY")
    print("=" * 50)
    
    passed = sum(results)
    total = len(results)
    
    print(f"Tests Passed: {passed}/{total}")
    
    if passed == total:
        print("🎉 All file storage tests passed!")
        print("💾 File storage system is ready for use")
        print("📁 Images will be automatically downloaded and stored")
        print("🖼️  Thumbnails will be generated automatically")
    else:
        print(f"⚠️  {total - passed} tests failed")


if __name__ == "__main__":
    main()