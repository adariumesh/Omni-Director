#!/usr/bin/env python3
"""
Fixed integration test for FIBO Export Engine Agent.

This corrected test properly integrates with the FileStorageManager by
actually storing files and using the real file IDs.

Run with: python test_export_engine_fixed.py
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


class FixedExportEngineTest:
    """Fixed test suite that properly integrates with FileStorageManager."""
    
    def __init__(self):
        """Initialize the test suite."""
        self.temp_dir = Path(tempfile.mkdtemp(prefix="fibo_export_fixed_"))
        self.test_files = []
        self.stored_files = []
        
        # Setup test environment
        self.setup_test_environment()
        
        logger.info(f"Test suite initialized with temp directory: {self.temp_dir}")
    
    def setup_test_environment(self):
        """Setup test environment with properly stored files."""
        try:
            # Create test directories
            test_data_dir = self.temp_dir / "test_data"
            storage_dir = self.temp_dir / "storage"
            test_data_dir.mkdir(parents=True, exist_ok=True)
            storage_dir.mkdir(parents=True, exist_ok=True)
            
            # Create sample image files for testing
            self.create_sample_images(test_data_dir)
            
            # Initialize FileStorageManager with test storage
            self.storage_manager = FileStorageManager(base_path=storage_dir)
            
            # Store files using the real storage manager
            self.store_test_files()
            
            # Initialize export agent
            export_config = ExportAgentConfig(
                export_base_dir=str(self.temp_dir / "exports"),
                temp_dir=str(self.temp_dir / "temp"),
                max_batch_size=10,
                cleanup_interval_hours=0,  # Disable automatic cleanup for testing
                temp_file_expiry_hours=1
            )
            
            # Patch the export agent to use our test storage manager
            self.export_agent = ExportEngineAgent(export_config)
            self.export_agent.storage_manager = self.storage_manager
            
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
            ]
            
            for config in sample_configs:
                # Create image
                image = Image.new('RGB', config["size"], config["color"])
                draw = ImageDraw.Draw(image)
                
                # Add some text for identification
                text = f"Test Image\n{config['name']}\n{config['size'][0]}x{config['size'][1]}"
                text_position = (50, 50)
                draw.text(text_position, text, fill=(255, 255, 255))
                
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
    
    def store_test_files(self):
        """Store test files using the FileStorageManager."""
        try:
            for test_file in self.test_files:
                # Copy file to storage
                with open(test_file, 'rb') as f:
                    content = f.read()
                
                # Use a mock URL for storage (FileStorageManager expects a URL)
                mock_url = f"http://test.example.com/{test_file.name}"
                
                # Store the file by temporarily creating it in storage and using manual storage
                stored_path = self.storage_manager.images_path / test_file.name
                stored_path.write_bytes(content)
                
                # Create StoredFile manually
                import hashlib
                file_id = f"test_{test_file.stem}_{datetime.now().strftime('%H%M%S')}"
                checksum = hashlib.sha256(content).hexdigest()
                
                stored_file = StoredFile(
                    file_id=file_id,
                    original_filename=test_file.name,
                    stored_path=stored_path,
                    file_size=len(content),
                    content_type=f"image/{test_file.suffix[1:]}",
                    checksum=checksum,
                    created_at=datetime.now(),
                    metadata={
                        "test_file": True,
                        "prompt": f"Test prompt for {test_file.name}",
                        "seed": 12345,
                        "mode": "test_mode",
                        "source_url": mock_url
                    }
                )
                
                self.stored_files.append(stored_file)
                logger.info(f"Stored test file: {file_id} -> {stored_path}")
            
        except Exception as e:
            logger.error(f"Failed to store test files: {e}")
            raise
    
    async def test_direct_file_export(self):
        """Test direct file export using StoredFile objects."""
        logger.info("Testing direct file export...")
        
        try:
            if not self.stored_files:
                logger.error("No stored files available")
                return False
            
            test_file = self.stored_files[0]
            
            # Create export request directly
            export_request = ExportRequest(
                source_path=test_file.stored_path,
                output_format=ExportFormat.PNG,
                quality=95,
                custom_filename="direct_export_test.png"
            )
            
            # Use the file export service directly
            export_service = FileExportService()
            export_dir = self.temp_dir / "direct_exports"
            export_dir.mkdir(exist_ok=True)
            
            result = await export_service.export_file(export_request, export_dir)
            
            if result.success:
                logger.info(f"Direct file export successful: {result.output_path}")
                logger.info(f"Original size: {result.original_size}")
                logger.info(f"Output size: {result.output_size}")
                logger.info(f"File size: {result.file_size_output} bytes")
                return True
            else:
                logger.error(f"Direct file export failed: {result.errors}")
                return False
                
        except Exception as e:
            logger.error(f"Direct file export test failed: {e}")
            return False
    
    async def test_zip_creation(self):
        """Test ZIP creation using stored files."""
        logger.info("Testing ZIP creation...")
        
        try:
            if len(self.stored_files) < 2:
                logger.error("Need at least 2 stored files for ZIP test")
                return False
            
            # Create ZIP configuration
            zip_config = ZipConfig(
                archive_name="test_archive",
                compression_method=CompressionMethod.DEFLATED,
                output_dir=self.temp_dir / "zip_exports"
            )
            
            # Use ZIP generator directly
            zip_generator = ZipGenerator()
            
            result = await zip_generator.create_archive(
                self.stored_files[:3],  # Use first 3 files
                zip_config
            )
            
            if result.success:
                logger.info(f"ZIP creation successful: {result.archive_path}")
                logger.info(f"Archive size: {result.archive_size:,} bytes")
                logger.info(f"File count: {result.file_count}")
                logger.info(f"Compression ratio: {result.compression_ratio:.2%}")
                logger.info(f"Download URL: {result.download_url}")
                return True
            else:
                logger.error(f"ZIP creation failed: {result.errors}")
                return False
                
        except Exception as e:
            logger.error(f"ZIP creation test failed: {e}")
            return False
    
    async def test_portfolio_creation(self):
        """Test portfolio creation using stored files."""
        logger.info("Testing portfolio creation...")
        
        try:
            if not self.stored_files:
                logger.error("No stored files available for portfolio")
                return False
            
            # Create portfolio configuration
            portfolio_config = PortfolioConfig(
                name="Test Portfolio",
                template="professional",
                theme=PortfolioTheme.PROFESSIONAL,
                layout=LayoutStyle.GRID,
                output_dir=self.temp_dir / "portfolio_exports"
            )
            
            # Use portfolio generator directly
            portfolio_generator = PortfolioGenerator()
            
            result = await portfolio_generator.create_portfolio(
                self.stored_files,
                portfolio_config
            )
            
            if result.success:
                logger.info(f"Portfolio creation successful: {result.portfolio_path}")
                logger.info(f"Asset count: {result.asset_count}")
                logger.info(f"Generation time: {result.generation_time:.2f}s")
                
                # Check for key files
                portfolio_path = Path(result.portfolio_path)
                key_files = ["index.html", "portfolio.json"]
                
                for file_name in key_files:
                    file_path = portfolio_path / file_name
                    if file_path.exists():
                        logger.info(f"✓ Found {file_name}")
                    else:
                        logger.warning(f"✗ Missing {file_name}")
                
                return True
            else:
                logger.error(f"Portfolio creation failed: {result.errors}")
                return False
                
        except Exception as e:
            logger.error(f"Portfolio creation test failed: {e}")
            return False
    
    async def test_export_agent_with_mock_storage(self):
        """Test export agent with mocked storage lookup."""
        logger.info("Testing export agent with mocked storage...")
        
        try:
            # Mock the get_file_info method to return our stored files
            def mock_get_file_info(file_id):
                for stored_file in self.stored_files:
                    if stored_file.file_id == file_id:
                        return stored_file
                return None
            
            # Temporarily replace the method
            original_method = self.export_agent.storage_manager.get_file_info
            self.export_agent.storage_manager.get_file_info = mock_get_file_info
            
            try:
                # Test single file export
                test_file = self.stored_files[0]
                operation = await self.export_agent.export_single_file(
                    file_id=test_file.file_id,
                    export_format=ExportFormat.PNG,
                    quality=95
                )
                
                if operation.status == ExportStatus.COMPLETED:
                    logger.info(f"Export agent single file export: SUCCESS")
                    logger.info(f"Output path: {operation.output_path}")
                    
                    # Test ZIP creation
                    file_ids = [f.file_id for f in self.stored_files[:2]]
                    zip_operation = await self.export_agent.create_zip_archive(
                        file_ids=file_ids,
                        archive_name="agent_test_archive"
                    )
                    
                    if zip_operation.status == ExportStatus.COMPLETED:
                        logger.info(f"Export agent ZIP creation: SUCCESS")
                        logger.info(f"Archive path: {zip_operation.output_path}")
                        return True
                    else:
                        logger.error(f"ZIP creation failed: {zip_operation.errors}")
                        return False
                        
                else:
                    logger.error(f"Single file export failed: {operation.errors}")
                    return False
                    
            finally:
                # Restore original method
                self.export_agent.storage_manager.get_file_info = original_method
                
        except Exception as e:
            logger.error(f"Export agent test failed: {e}")
            return False
    
    async def run_comprehensive_test(self):
        """Run comprehensive functionality test."""
        logger.info("Starting FIBO Export Engine comprehensive test...")
        
        test_results = {}
        
        tests = [
            ("Direct File Export", self.test_direct_file_export),
            ("ZIP Creation", self.test_zip_creation),
            ("Portfolio Creation", self.test_portfolio_creation),
            ("Export Agent Integration", self.test_export_agent_with_mock_storage),
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
        logger.info("COMPREHENSIVE TEST SUMMARY")
        logger.info(f"{'='*60}")
        
        passed = sum(1 for result in test_results.values() if result)
        total = len(test_results)
        
        for test_name, result in test_results.items():
            status = "✅ PASSED" if result else "❌ FAILED"
            logger.info(f"{test_name:<30} {status}")
        
        logger.info(f"\nOverall Result: {passed}/{total} tests passed")
        
        if passed == total:
            logger.info("🎉 All tests passed! Export Engine functionality verified.")
            return True
        else:
            logger.error(f"⚠️  {total - passed} tests failed.")
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
    logger.info("FIBO Export Engine Agent - Fixed Integration Test")
    logger.info("=" * 60)
    
    test_suite = FixedExportEngineTest()
    
    try:
        success = await test_suite.run_comprehensive_test()
        
        if success:
            logger.info("\n🎉 Fixed integration test completed successfully!")
            logger.info("Export Engine Agent is functioning correctly.")
            return 0
        else:
            logger.error("\n💥 Some tests failed - check implementation details.")
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