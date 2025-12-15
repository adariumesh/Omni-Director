#!/usr/bin/env python3
"""
Simplified test for FIBO Export Engine components.

This test directly tests the core export functionality without
importing all the orchestrator agents.

Run with: python test_export_simple.py
"""

import asyncio
import logging
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
import sys

# Add the backend directory to Python path
sys.path.insert(0, '/Users/adariprasad/weapon/Omni - Director/backend')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import only what we need
try:
    from app.services.file_storage import StoredFile
    from orchestrator.agents.file_export_service import FileExportService, ExportFormat, ExportRequest
    from orchestrator.agents.zip_generator import ZipGenerator, ZipConfig, CompressionMethod
    from orchestrator.agents.portfolio_generator import (
        PortfolioGenerator, PortfolioConfig, PortfolioTheme, LayoutStyle
    )
except ImportError as e:
    logger.error(f"Failed to import modules: {e}")
    sys.exit(1)


class SimpleExportTest:
    """Simplified test for core export functionality."""
    
    def __init__(self):
        self.temp_dir = Path(tempfile.mkdtemp(prefix="fibo_simple_test_"))
        self.test_files = []
        self.stored_files = []
        
        self.setup_test_environment()
        logger.info(f"Simple test initialized: {self.temp_dir}")
    
    def setup_test_environment(self):
        """Setup test environment."""
        try:
            # Create test images
            self.create_sample_images()
            
            # Create stored file objects
            self.create_stored_files()
            
            logger.info("Test environment ready")
            
        except Exception as e:
            logger.error(f"Setup failed: {e}")
            raise
    
    def create_sample_images(self):
        """Create test images."""
        try:
            from PIL import Image, ImageDraw
            
            configs = [
                {"name": "test1.png", "size": (400, 400), "color": (255, 0, 0)},
                {"name": "test2.jpg", "size": (600, 400), "color": (0, 255, 0)},
                {"name": "test3.png", "size": (800, 600), "color": (0, 0, 255)},
            ]
            
            for config in configs:
                image = Image.new('RGB', config["size"], config["color"])
                draw = ImageDraw.Draw(image)
                draw.text((50, 50), f"Test: {config['name']}", fill=(255, 255, 255))
                
                image_path = self.temp_dir / config["name"]
                if config["name"].endswith('.jpg'):
                    image.save(image_path, 'JPEG', quality=95)
                else:
                    image.save(image_path, 'PNG')
                
                self.test_files.append(image_path)
                logger.info(f"Created: {config['name']}")
                
        except Exception as e:
            logger.error(f"Image creation failed: {e}")
            raise
    
    def create_stored_files(self):
        """Create StoredFile objects for testing."""
        try:
            for i, test_file in enumerate(self.test_files):
                stored_file = StoredFile(
                    file_id=f"test_file_{i+1}",
                    original_filename=test_file.name,
                    stored_path=test_file,
                    file_size=test_file.stat().st_size,
                    content_type=f"image/{'jpeg' if test_file.suffix == '.jpg' else 'png'}",
                    checksum="test_checksum",
                    created_at=datetime.now(),
                    metadata={
                        "prompt": f"Test image {i+1}",
                        "seed": 12345 + i,
                        "mode": "test"
                    }
                )
                self.stored_files.append(stored_file)
                logger.info(f"Created StoredFile: {stored_file.file_id}")
                
        except Exception as e:
            logger.error(f"StoredFile creation failed: {e}")
            raise
    
    async def test_file_export_service(self):
        """Test FileExportService."""
        logger.info("Testing FileExportService...")
        
        try:
            export_service = FileExportService()
            test_file = self.stored_files[0]
            
            export_request = ExportRequest(
                source_path=test_file.stored_path,
                output_format=ExportFormat.PNG,
                quality=95,
                custom_filename="export_test.png"
            )
            
            output_dir = self.temp_dir / "exports"
            result = await export_service.export_file(export_request, output_dir)
            
            if result.success:
                logger.info(f"✅ Export successful: {result.output_path}")
                logger.info(f"   Original: {result.original_size}")
                logger.info(f"   Output: {result.output_size}")
                logger.info(f"   Size: {result.file_size_output} bytes")
                return True
            else:
                logger.error(f"❌ Export failed: {result.errors}")
                return False
                
        except Exception as e:
            logger.error(f"FileExportService test failed: {e}")
            return False
    
    async def test_zip_generator(self):
        """Test ZipGenerator."""
        logger.info("Testing ZipGenerator...")
        
        try:
            zip_generator = ZipGenerator()
            
            config = ZipConfig(
                archive_name="test_archive",
                compression_method=CompressionMethod.DEFLATED,
                output_dir=self.temp_dir / "zips"
            )
            
            result = await zip_generator.create_archive(self.stored_files, config)
            
            if result.success:
                logger.info(f"✅ ZIP creation successful: {result.archive_path}")
                logger.info(f"   Size: {result.archive_size:,} bytes")
                logger.info(f"   Files: {result.file_count}")
                logger.info(f"   Compression: {result.compression_ratio:.2%}")
                return True
            else:
                logger.error(f"❌ ZIP creation failed: {result.errors}")
                return False
                
        except Exception as e:
            logger.error(f"ZipGenerator test failed: {e}")
            return False
    
    async def test_portfolio_generator(self):
        """Test PortfolioGenerator."""
        logger.info("Testing PortfolioGenerator...")
        
        try:
            portfolio_generator = PortfolioGenerator()
            
            config = PortfolioConfig(
                name="Test Portfolio",
                theme=PortfolioTheme.PROFESSIONAL,
                layout=LayoutStyle.GRID,
                output_dir=self.temp_dir / "portfolios"
            )
            
            result = await portfolio_generator.create_portfolio(self.stored_files, config)
            
            if result.success:
                logger.info(f"✅ Portfolio creation successful: {result.portfolio_path}")
                logger.info(f"   Assets: {result.asset_count}")
                logger.info(f"   Time: {result.generation_time:.2f}s")
                
                # Check key files
                portfolio_path = Path(result.portfolio_path)
                index_file = portfolio_path / "index.html"
                if index_file.exists():
                    logger.info(f"   ✓ index.html exists ({index_file.stat().st_size} bytes)")
                else:
                    logger.warning("   ✗ index.html missing")
                
                return True
            else:
                logger.error(f"❌ Portfolio creation failed: {result.errors}")
                return False
                
        except Exception as e:
            logger.error(f"PortfolioGenerator test failed: {e}")
            return False
    
    async def run_all_tests(self):
        """Run all tests."""
        logger.info("Starting FIBO Export Engine Simple Tests")
        logger.info("=" * 50)
        
        tests = [
            ("File Export Service", self.test_file_export_service),
            ("ZIP Generator", self.test_zip_generator),
            ("Portfolio Generator", self.test_portfolio_generator),
        ]
        
        results = {}
        for test_name, test_func in tests:
            logger.info(f"\n--- {test_name} ---")
            try:
                result = await test_func()
                results[test_name] = result
            except Exception as e:
                logger.error(f"{test_name} failed: {e}")
                results[test_name] = False
        
        # Summary
        logger.info(f"\n{'='*50}")
        logger.info("TEST RESULTS")
        logger.info(f"{'='*50}")
        
        passed = 0
        for test_name, result in results.items():
            status = "PASS" if result else "FAIL"
            logger.info(f"{test_name:<25} {status}")
            if result:
                passed += 1
        
        total = len(results)
        logger.info(f"\nPassed: {passed}/{total}")
        
        if passed == total:
            logger.info("🎉 All tests passed!")
            return True
        else:
            logger.error(f"⚠️ {total - passed} tests failed")
            return False
    
    def cleanup(self):
        """Clean up test files."""
        try:
            if self.temp_dir.exists():
                shutil.rmtree(self.temp_dir)
                logger.info(f"Cleaned up: {self.temp_dir}")
        except Exception as e:
            logger.warning(f"Cleanup failed: {e}")


async def main():
    """Main test function."""
    test = SimpleExportTest()
    
    try:
        success = await test.run_all_tests()
        return 0 if success else 1
    finally:
        test.cleanup()


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)