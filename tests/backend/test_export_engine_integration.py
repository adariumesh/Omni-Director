#!/usr/bin/env python3
"""
Test script for FIBO Export Engine Agent integration.

This script tests the complete export functionality including:
- Integration with FileStorageManager
- File export service functionality
- ZIP generation capabilities
- Portfolio creation
- Download URL management
- Cleanup operations

Run with: python test_export_engine_integration.py
"""

import asyncio
import logging
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
import sys
import os

# Add the backend directory to Python path
sys.path.insert(0, '/Users/adariprasad/weapon/Omni - Director/backend')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import FIBO modules
try:
    from app.services.file_storage import FileStorageManager, StoredFile
    from orchestrator.agents.export_engine_agent import (
        ExportEngineAgent, ExportAgentConfig, ExportType, ExportStatus
    )
    from orchestrator.agents.file_export_service import (
        FileExportService, ExportFormat, ExportRequest
    )
    from orchestrator.agents.zip_generator import (
        ZipGenerator, ZipConfig, CompressionMethod
    )
    from orchestrator.agents.portfolio_generator import (
        PortfolioGenerator, PortfolioConfig, PortfolioTheme, LayoutStyle
    )
except ImportError as e:
    logger.error(f"Failed to import FIBO modules: {e}")
    logger.error("Please ensure you're running from the correct directory")
    sys.exit(1)


class ExportEngineTestSuite:
    """Comprehensive test suite for the Export Engine Agent."""
    
    def __init__(self):
        """Initialize the test suite."""
        self.temp_dir = Path(tempfile.mkdtemp(prefix="fibo_export_test_"))
        self.test_files = []
        
        # Setup test environment
        self.setup_test_environment()
        
        logger.info(f"Test suite initialized with temp directory: {self.temp_dir}")
    
    def setup_test_environment(self):
        """Setup test environment with sample files."""
        try:
            # Create test directories
            test_data_dir = self.temp_dir / "test_data"
            test_data_dir.mkdir(parents=True, exist_ok=True)
            
            # Create sample image files for testing
            self.create_sample_images(test_data_dir)
            
            # Initialize services with test configuration
            self.storage_manager = FileStorageManager(base_path=test_data_dir / "storage")
            
            export_config = ExportAgentConfig(
                export_base_dir=str(self.temp_dir / "exports"),
                temp_dir=str(self.temp_dir / "temp"),
                max_batch_size=10,
                cleanup_interval_hours=0,  # Disable automatic cleanup for testing
                temp_file_expiry_hours=1
            )
            
            self.export_agent = ExportEngineAgent(export_config)
            
            logger.info("Test environment setup completed")
            
        except Exception as e:
            logger.error(f"Failed to setup test environment: {e}")
            raise
    
    def create_sample_images(self, data_dir: Path):
        """Create sample image files for testing."""
        try:
            from PIL import Image, ImageDraw
            
            # Create sample images with different properties
            sample_configs = [
                {"name": "test_image_1.png", "size": (512, 512), "color": (255, 100, 100)},
                {"name": "test_image_2.jpg", "size": (768, 768), "color": (100, 255, 100)},
                {"name": "test_image_3.png", "size": (1024, 768), "color": (100, 100, 255)},
                {"name": "test_image_4.webp", "size": (640, 640), "color": (255, 255, 100)},
                {"name": "test_image_5.png", "size": (800, 600), "color": (255, 100, 255)},
            ]
            
            for config in sample_configs:
                # Create image
                image = Image.new('RGB', config["size"], config["color"])
                draw = ImageDraw.Draw(image)
                
                # Add some text for identification
                text = f"Test Image\n{config['name']}\n{config['size'][0]}x{config['size'][1]}"
                text_position = (50, 50)
                draw.text(text_position, text, fill=(0, 0, 0))
                
                # Save image
                image_path = data_dir / config["name"]
                
                # Save with appropriate format
                if config["name"].endswith('.jpg'):
                    image.save(image_path, 'JPEG', quality=95)
                elif config["name"].endswith('.webp'):
                    image.save(image_path, 'WEBP', quality=95)
                else:
                    image.save(image_path, 'PNG')
                
                self.test_files.append(image_path)
                logger.info(f"Created test image: {config['name']} ({config['size'][0]}x{config['size'][1]})")
            
        except Exception as e:
            logger.error(f"Failed to create sample images: {e}")
            raise
    
    async def test_file_storage_integration(self):
        """Test integration with FileStorageManager."""
        logger.info("Testing FileStorageManager integration...")
        
        try:
            stored_files = []
            
            # Store test files using FileStorageManager
            for test_file in self.test_files:
                # Simulate storing downloaded files
                with open(test_file, 'rb') as f:
                    content = f.read()
                
                # Create a temporary stored file entry
                stored_file = StoredFile(
                    file_id=f"test_{test_file.stem}_{datetime.now().strftime('%H%M%S')}",
                    original_filename=test_file.name,
                    stored_path=test_file,
                    file_size=len(content),
                    content_type=f"image/{test_file.suffix[1:]}",
                    checksum="test_checksum",
                    created_at=datetime.utcnow(),
                    metadata={
                        "test_file": True,
                        "prompt": f"Test prompt for {test_file.name}",
                        "seed": 12345,
                        "mode": "test_mode"
                    }
                )
                
                stored_files.append(stored_file)
                logger.info(f"Prepared stored file: {stored_file.file_id}")
            
            self.stored_files = stored_files
            logger.info(f"FileStorageManager integration test passed: {len(stored_files)} files prepared")
            return True
            
        except Exception as e:
            logger.error(f"FileStorageManager integration test failed: {e}")
            return False
    
    async def test_single_file_export(self):
        """Test single file export functionality."""
        logger.info("Testing single file export...")
        
        try:
            if not hasattr(self, 'stored_files') or not self.stored_files:
                logger.error("No stored files available for testing")
                return False
            
            test_file = self.stored_files[0]
            
            # Test PNG export
            operation = await self.export_agent.export_single_file(
                file_id=test_file.file_id,
                export_format=ExportFormat.PNG,
                quality=95,
                custom_filename="exported_test_image.png"
            )
            
            if operation.status == ExportStatus.COMPLETED:
                logger.info(f"Single file export successful: {operation.output_path}")
                
                # Verify file exists
                if operation.output_path and Path(operation.output_path).exists():
                    logger.info("Exported file verified to exist")
                    return True
                else:
                    logger.error("Exported file not found")
                    return False
            else:
                logger.error(f"Single file export failed: {operation.errors}")
                return False
                
        except Exception as e:
            logger.error(f"Single file export test failed: {e}")
            return False
    
    async def test_batch_export(self):
        """Test batch file export functionality."""
        logger.info("Testing batch file export...")
        
        try:
            if not hasattr(self, 'stored_files') or len(self.stored_files) < 3:
                logger.error("Not enough stored files for batch testing")
                return False
            
            # Select multiple files for batch export
            file_ids = [f.file_id for f in self.stored_files[:3]]
            
            # Progress callback for testing
            progress_values = []
            def progress_callback(progress):
                progress_values.append(progress)
                logger.info(f"Batch export progress: {progress:.1%}")
            
            operation = await self.export_agent.export_batch_images(
                file_ids=file_ids,
                export_format=ExportFormat.JPEG,
                quality=90,
                progress_callback=progress_callback
            )
            
            if operation.status == ExportStatus.COMPLETED:
                logger.info(f"Batch export successful: {operation.processed_files}/{operation.total_files} files")
                logger.info(f"Output directory: {operation.output_path}")
                logger.info(f"Progress callbacks received: {len(progress_values)}")
                return True
            else:
                logger.error(f"Batch export failed: {operation.errors}")
                return False
                
        except Exception as e:
            logger.error(f"Batch export test failed: {e}")
            return False
    
    async def test_zip_generation(self):
        """Test ZIP archive generation."""
        logger.info("Testing ZIP generation...")
        
        try:
            if not hasattr(self, 'stored_files') or len(self.stored_files) < 2:
                logger.error("Not enough stored files for ZIP testing")
                return False
            
            file_ids = [f.file_id for f in self.stored_files[:4]]
            
            operation = await self.export_agent.create_zip_archive(
                file_ids=file_ids,
                archive_name="test_archive",
                include_metadata=True,
                compression_level=6
            )
            
            if operation.status == ExportStatus.COMPLETED:
                logger.info(f"ZIP generation successful: {operation.output_path}")
                logger.info(f"Download URL: {operation.download_url}")
                logger.info(f"Archive size: {operation.metadata.get('archive_size', 'unknown')} bytes")
                logger.info(f"Compression ratio: {operation.metadata.get('compression_ratio', 'unknown')}")
                
                # Verify ZIP file exists and has content
                if operation.output_path and Path(operation.output_path).exists():
                    zip_size = Path(operation.output_path).stat().st_size
                    if zip_size > 0:
                        logger.info(f"ZIP file verified: {zip_size:,} bytes")
                        return True
                    else:
                        logger.error("ZIP file is empty")
                        return False
                else:
                    logger.error("ZIP file not found")
                    return False
            else:
                logger.error(f"ZIP generation failed: {operation.errors}")
                return False
                
        except Exception as e:
            logger.error(f"ZIP generation test failed: {e}")
            return False
    
    async def test_portfolio_generation(self):
        """Test HTML portfolio generation."""
        logger.info("Testing portfolio generation...")
        
        try:
            if not hasattr(self, 'stored_files') or len(self.stored_files) < 2:
                logger.error("Not enough stored files for portfolio testing")
                return False
            
            file_ids = [f.file_id for f in self.stored_files]
            
            operation = await self.export_agent.create_html_portfolio(
                file_ids=file_ids,
                portfolio_name="Test Portfolio",
                template="professional",
                custom_config={
                    "theme": "professional",
                    "layout": "grid",
                    "include_metadata": True,
                    "show_prompts": True
                }
            )
            
            if operation.status == ExportStatus.COMPLETED:
                logger.info(f"Portfolio generation successful: {operation.output_path}")
                logger.info(f"Portfolio URL: {operation.metadata.get('portfolio_url')}")
                logger.info(f"Asset count: {operation.metadata.get('asset_count')}")
                
                # Verify portfolio files exist
                portfolio_path = Path(operation.output_path)
                index_file = portfolio_path / "index.html"
                
                if index_file.exists():
                    logger.info("Portfolio index.html verified")
                    
                    # Check for other expected files
                    expected_files = [
                        "css/style.css",
                        "js/script.js", 
                        "portfolio.json"
                    ]
                    
                    missing_files = []
                    for file_path in expected_files:
                        if not (portfolio_path / file_path).exists():
                            missing_files.append(file_path)
                    
                    if missing_files:
                        logger.warning(f"Some portfolio files missing: {missing_files}")
                    else:
                        logger.info("All expected portfolio files found")
                    
                    return True
                else:
                    logger.error("Portfolio index.html not found")
                    return False
            else:
                logger.error(f"Portfolio generation failed: {operation.errors}")
                return False
                
        except Exception as e:
            logger.error(f"Portfolio generation test failed: {e}")
            return False
    
    async def test_operation_management(self):
        """Test operation tracking and management."""
        logger.info("Testing operation management...")
        
        try:
            # Get operation statistics
            stats = self.export_agent.get_export_statistics()
            logger.info(f"Export statistics: {stats}")
            
            # List operations
            operations = self.export_agent.list_operations()
            logger.info(f"Total operations tracked: {len(operations)}")
            
            # Test operation status for each
            for operation in operations[:3]:  # Check first 3 operations
                status = self.export_agent.get_operation_status(operation.operation_id)
                if status:
                    logger.info(f"Operation {operation.operation_id}: {status.status.value}")
                else:
                    logger.warning(f"Operation {operation.operation_id} not found")
            
            return True
            
        except Exception as e:
            logger.error(f"Operation management test failed: {e}")
            return False
    
    async def test_cleanup_functionality(self):
        """Test cleanup functionality."""
        logger.info("Testing cleanup functionality...")
        
        try:
            # Perform cleanup
            cleaned_count = self.export_agent.cleanup_expired_files()
            logger.info(f"Cleanup completed: {cleaned_count} items cleaned")
            
            # Test storage stats
            storage_stats = self.storage_manager.get_storage_stats()
            logger.info(f"Storage statistics: {storage_stats}")
            
            return True
            
        except Exception as e:
            logger.error(f"Cleanup test failed: {e}")
            return False
    
    async def test_error_handling(self):
        """Test error handling scenarios."""
        logger.info("Testing error handling...")
        
        try:
            # Test with non-existent file
            operation = await self.export_agent.export_single_file(
                file_id="non_existent_file_id",
                export_format=ExportFormat.PNG
            )
            
            if operation.status == ExportStatus.FAILED:
                logger.info("Non-existent file error handling: PASSED")
                logger.info(f"Error message: {operation.errors}")
            else:
                logger.error("Expected failure for non-existent file")
                return False
            
            # Test with empty file list
            operation = await self.export_agent.create_zip_archive(
                file_ids=[],
                archive_name="empty_archive"
            )
            
            if operation.status == ExportStatus.FAILED:
                logger.info("Empty file list error handling: PASSED")
            else:
                logger.error("Expected failure for empty file list")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error handling test failed: {e}")
            return False
    
    async def run_all_tests(self):
        """Run all tests in the test suite."""
        logger.info("Starting FIBO Export Engine Agent test suite...")
        
        test_results = {}
        
        tests = [
            ("File Storage Integration", self.test_file_storage_integration),
            ("Single File Export", self.test_single_file_export),
            ("Batch Export", self.test_batch_export),
            ("ZIP Generation", self.test_zip_generation),
            ("Portfolio Generation", self.test_portfolio_generation),
            ("Operation Management", self.test_operation_management),
            ("Cleanup Functionality", self.test_cleanup_functionality),
            ("Error Handling", self.test_error_handling),
        ]
        
        for test_name, test_function in tests:
            logger.info(f"\n{'='*60}")
            logger.info(f"Running test: {test_name}")
            logger.info(f"{'='*60}")
            
            try:
                result = await test_function()
                test_results[test_name] = result
                
                if result:
                    logger.info(f"✅ {test_name}: PASSED")
                else:
                    logger.error(f"❌ {test_name}: FAILED")
                    
            except Exception as e:
                logger.error(f"💥 {test_name}: ERROR - {e}")
                test_results[test_name] = False
        
        # Print summary
        logger.info(f"\n{'='*60}")
        logger.info("TEST SUITE SUMMARY")
        logger.info(f"{'='*60}")
        
        passed = sum(1 for result in test_results.values() if result)
        total = len(test_results)
        
        for test_name, result in test_results.items():
            status = "✅ PASSED" if result else "❌ FAILED"
            logger.info(f"{test_name:<30} {status}")
        
        logger.info(f"\nOverall Result: {passed}/{total} tests passed")
        
        if passed == total:
            logger.info("🎉 All tests passed! Export Engine Agent is working correctly.")
            return True
        else:
            logger.error(f"⚠️  {total - passed} tests failed. Please review the issues above.")
            return False
    
    def cleanup_test_environment(self):
        """Clean up test environment."""
        try:
            if self.temp_dir.exists():
                shutil.rmtree(self.temp_dir)
                logger.info(f"Cleaned up test directory: {self.temp_dir}")
        except Exception as e:
            logger.warning(f"Failed to cleanup test directory: {e}")


async def main():
    """Main test execution function."""
    logger.info("FIBO Export Engine Agent - Integration Test Suite")
    logger.info("=" * 60)
    
    test_suite = ExportEngineTestSuite()
    
    try:
        success = await test_suite.run_all_tests()
        
        if success:
            logger.info("\n🎉 Integration test suite completed successfully!")
            return 0
        else:
            logger.error("\n💥 Integration test suite failed!")
            return 1
            
    except Exception as e:
        logger.error(f"Test suite execution failed: {e}")
        return 1
        
    finally:
        test_suite.cleanup_test_environment()


if __name__ == "__main__":
    # Run the test suite
    exit_code = asyncio.run(main())
    sys.exit(exit_code)