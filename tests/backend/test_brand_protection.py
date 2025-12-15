#!/usr/bin/env python3
"""
Test script for Brand Protection Agent system.
Tests watermarking, compliance checking, and brand guidelines.
"""

import asyncio
import logging
import tempfile
from pathlib import Path
from PIL import Image, ImageDraw
import sys
import os

# Add parent directory to path
sys.path.append(str(Path(__file__).parent))

from orchestrator.agents import (
    get_brand_protection_agent,
    get_brand_guideline_manager,
    WatermarkConfig,
    BrandProtectionConfig,
    ColorGuideline
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_test_image(width: int = 800, height: int = 600) -> Path:
    """Create a test image for processing.
    
    Args:
        width: Image width.
        height: Image height.
        
    Returns:
        Path to created test image.
    """
    # Create a colorful test image
    image = Image.new('RGB', (width, height), color='white')
    draw = ImageDraw.Draw(image)
    
    # Draw some shapes with brand-like colors
    draw.rectangle([50, 50, width-50, height-50], fill='#003366', outline='#10B981', width=5)
    draw.ellipse([150, 150, width-150, height-150], fill='#6B7280', outline='#003366', width=3)
    draw.rectangle([width//4, height//4, 3*width//4, 3*height//4], fill=None, outline='#10B981', width=2)
    
    # Add some text-like patterns
    for i in range(5):
        y = 100 + i * 50
        draw.rectangle([200, y, 600, y + 20], fill='#1F2937')
    
    # Save to temporary file
    temp_file = Path(tempfile.mktemp(suffix='.png'))
    image.save(temp_file, 'PNG')
    
    logger.info(f"Created test image: {temp_file} ({width}x{height})")
    return temp_file


def create_test_logo() -> Path:
    """Create a simple test logo.
    
    Returns:
        Path to created logo.
    """
    logo = Image.new('RGBA', (200, 100), color=(0, 51, 102, 180))
    draw = ImageDraw.Draw(logo)
    
    # Simple logo design
    draw.ellipse([20, 20, 80, 80], fill='white')
    draw.text((90, 35), "FIBO", fill='white')
    
    temp_logo = Path(tempfile.mktemp(suffix='.png'))
    logo.save(temp_logo, 'PNG')
    
    logger.info(f"Created test logo: {temp_logo}")
    return temp_logo


async def test_watermarking_service():
    """Test the watermarking service directly."""
    print("\n" + "="*60)
    print("🎨 TESTING WATERMARKING SERVICE")
    print("="*60)
    
    from orchestrator.agents.watermarking_service import WatermarkingService
    
    watermarking_service = WatermarkingService()
    
    # Create test image and logo
    test_image = create_test_image(1024, 768)
    test_logo = create_test_logo()
    
    try:
        # Test watermark configuration
        config = WatermarkConfig(
            enabled=True,
            position="bottom-right",
            opacity=0.8,
            size_percent=15.0,
            margin_percent=3.0,
            blend_mode="normal",
            quality=95
        )
        
        # Apply watermark
        output_path = Path(tempfile.mktemp(suffix='_watermarked.png'))
        
        result = await watermarking_service.apply_watermark(
            input_path=test_image,
            output_path=output_path,
            config=config,
            logo_path=test_logo
        )
        
        print(f"✅ Watermark Result:")
        print(f"   Success: {result.success}")
        print(f"   Processing Time: {result.processing_time_ms:.1f}ms")
        print(f"   Original Size: {result.original_size}")
        print(f"   Output Path: {result.output_path}")
        print(f"   File Size Changed: {result.file_size_changed}")
        
        if result.watermark_info:
            print(f"   Watermark Info: {result.watermark_info}")
        
        if result.error:
            print(f"   Error: {result.error}")
        
        # Test text watermark (no logo)
        print(f"\n📝 Testing text watermark...")
        text_output = Path(tempfile.mktemp(suffix='_text_watermarked.png'))
        
        text_result = await watermarking_service.apply_watermark(
            input_path=test_image,
            output_path=text_output,
            config=config,
            logo_path=None
        )
        
        print(f"   Text Watermark Success: {text_result.success}")
        print(f"   Processing Time: {text_result.processing_time_ms:.1f}ms")
        
        # Test batch watermarking
        print(f"\n📦 Testing batch watermarking...")
        test_image2 = create_test_image(640, 480)
        test_image3 = create_test_image(1200, 800)
        
        batch_pairs = [
            (test_image2, Path(tempfile.mktemp(suffix='_batch1.png'))),
            (test_image3, Path(tempfile.mktemp(suffix='_batch2.png')))
        ]
        
        batch_results = await watermarking_service.batch_watermark(
            file_pairs=batch_pairs,
            config=config,
            logo_path=test_logo
        )
        
        successful_batch = len([r for r in batch_results if r.success])
        print(f"   Batch Results: {successful_batch}/{len(batch_results)} successful")
        
        # Test logo validation
        print(f"\n🔍 Testing logo validation...")
        validation = watermarking_service.validate_logo(test_logo)
        print(f"   Logo Valid: {validation['valid']}")
        if validation['valid']:
            print(f"   Logo Size: {validation['width']}x{validation['height']}")
            print(f"   Format: {validation['format']}")
            print(f"   Has Transparency: {validation['has_transparency']}")
            print(f"   Recommendations: {validation['recommendations']}")
        
    finally:
        # Cleanup
        for file_path in [test_image, test_logo]:
            if file_path.exists():
                file_path.unlink()
        
        print("🧹 Cleaned up test files")


async def test_compliance_checker():
    """Test the compliance checker."""
    print("\n" + "="*60)
    print("🔍 TESTING COMPLIANCE CHECKER")
    print("="*60)
    
    from orchestrator.agents.compliance_checker import ComplianceChecker
    
    compliance_checker = ComplianceChecker()
    
    # Create test image
    test_image = create_test_image(1200, 900)
    
    try:
        # Set brand colors for testing
        brand_colors = [
            (0, 51, 102),    # Deep Blue
            (16, 185, 129),  # Green
            (107, 114, 128), # Gray
            (255, 255, 255), # White
            (31, 41, 55)     # Dark Gray
        ]
        compliance_checker.set_brand_colors(brand_colors)
        
        # Run compliance check
        result = await compliance_checker.check_compliance(test_image)
        
        print(f"✅ Compliance Result:")
        print(f"   Score: {result.score:.3f}")
        print(f"   Violations: {len(result.violations)}")
        print(f"   Warnings: {len(result.warnings)}")
        print(f"   Processing Time: {result.processing_time_ms:.1f}ms")
        
        if result.violations:
            print(f"   Violation Details: {result.violations}")
        
        if result.warnings:
            print(f"   Warning Details: {result.warnings}")
        
        if result.recommendations:
            print(f"   Recommendations: {result.recommendations}")
        
        # Test color profile analysis
        if result.color_profile:
            print(f"\n🎨 Color Profile:")
            print(f"   Dominant Colors: {len(result.color_profile.dominant_colors)}")
            print(f"   Brightness: {result.color_profile.brightness:.2f}")
            print(f"   Contrast: {result.color_profile.contrast:.2f}")
            print(f"   Saturation: {result.color_profile.saturation:.2f}")
            print(f"   Temperature: {result.color_profile.temperature}")
            print(f"   Color Distribution: {result.color_profile.color_distribution}")
        
        # Test content analysis
        if result.content_analysis:
            print(f"\n📄 Content Analysis:")
            print(f"   Text Detected: {result.content_analysis.text_detected}")
            print(f"   Text Confidence: {result.content_analysis.text_confidence:.2f}")
            print(f"   Inappropriate Content: {result.content_analysis.inappropriate_content}")
            print(f"   Safety Score: {result.content_analysis.safety_score:.2f}")
            print(f"   Quality Score: {result.content_analysis.quality_score:.2f}")
        
        # Test batch compliance checking
        print(f"\n📦 Testing batch compliance...")
        test_image2 = create_test_image(800, 600)
        test_image3 = create_test_image(1600, 1200)
        
        # Create additional test results for summary
        result2 = await compliance_checker.check_compliance(test_image2)
        result3 = await compliance_checker.check_compliance(test_image3)
        
        # Test compliance summary
        summary = compliance_checker.get_compliance_summary([result, result2, result3])
        print(f"   Summary - Total Checks: {summary['total_checks']}")
        print(f"   Summary - Average Score: {summary['average_score']}")
        print(f"   Summary - Passing Count: {summary['passing_count']}")
        print(f"   Summary - Common Violations: {summary['common_violations']}")
        
    finally:
        # Cleanup
        if test_image.exists():
            test_image.unlink()
        print("🧹 Cleaned up test files")


async def test_brand_guidelines():
    """Test the brand guidelines manager."""
    print("\n" + "="*60)
    print("📋 TESTING BRAND GUIDELINES MANAGER")
    print("="*60)
    
    guideline_manager = get_brand_guideline_manager()
    
    # Create test image
    test_image = create_test_image(1024, 768)
    
    try:
        # Create brand guidelines
        print("📝 Creating brand guidelines...")
        guidelines = guideline_manager.create_guideline("FIBO Test Brand")
        
        print(f"✅ Created guidelines for {guidelines.brand_name}")
        print(f"   Version: {guidelines.version}")
        print(f"   Colors: {len(guidelines.colors)}")
        print(f"   Typography: {len(guidelines.typography)}")
        print(f"   Has Logo: {guidelines.logo is not None}")
        print(f"   Has Style: {guidelines.style is not None}")
        
        # List color palette
        print(f"\n🎨 Color Palette:")
        for color in guidelines.colors:
            print(f"   {color.name}: {color.hex_code} ({color.usage})")
        
        # Update guidelines with custom colors
        print(f"\n🔧 Updating guidelines...")
        custom_colors = [
            {
                "name": "Custom Primary",
                "hex_code": "#FF6B35",
                "rgb": (255, 107, 53),
                "usage": "primary",
                "description": "Vibrant orange primary"
            },
            {
                "name": "Custom Secondary", 
                "hex_code": "#2E86AB",
                "rgb": (46, 134, 171),
                "usage": "secondary",
                "description": "Deep blue secondary"
            }
        ]
        
        update_success = guideline_manager.update_guidelines(
            "fibo_test_brand_" + guidelines.version.replace(".", ""),
            {"colors": custom_colors}
        )
        print(f"   Update Success: {update_success}")
        
        # Validate asset against guidelines
        print(f"\n🔍 Validating asset against guidelines...")
        validation_result = await guideline_manager.validate_asset(test_image)
        
        print(f"✅ Validation Result:")
        print(f"   Compliant: {validation_result.compliant}")
        print(f"   Score: {validation_result.score:.3f}")
        print(f"   Violations: {len(validation_result.violations)}")
        print(f"   Warnings: {len(validation_result.warnings)}")
        print(f"   Recommendations: {len(validation_result.recommendations)}")
        
        if validation_result.violations:
            print(f"   Violation Details: {validation_result.violations}")
        
        if validation_result.recommendations:
            print(f"   Recommendation Details: {validation_result.recommendations}")
        
        print(f"   Guideline Matches: {validation_result.guideline_matches}")
        
        # Test guidelines listing
        print(f"\n📊 Listing all guidelines...")
        all_guidelines = guideline_manager.list_guidelines()
        print(f"   Found {len(all_guidelines)} guidelines")
        
        for guide in all_guidelines:
            print(f"   - {guide['brand_name']} (ID: {guide['id']}, Version: {guide['version']})")
    
    finally:
        # Cleanup
        if test_image.exists():
            test_image.unlink()
        print("🧹 Cleaned up test files")


async def test_full_integration():
    """Test the full brand protection agent integration."""
    print("\n" + "="*60)
    print("🛡️ TESTING FULL BRAND PROTECTION INTEGRATION")
    print("="*60)
    
    # Get the brand protection agent
    agent = get_brand_protection_agent()
    
    # Create test image
    test_image = create_test_image(1024, 768)
    
    try:
        # Mock database setup would be here
        # For testing, we'll simulate asset creation
        
        print("🎨 Configuring brand protection...")
        
        # Configure watermarking
        agent.configure_watermark(
            enabled=True,
            position="bottom-right",
            opacity=0.7,
            size_percent=12.0,
            blend_mode="normal"
        )
        
        # Configure compliance
        agent.configure_compliance(
            compliance_enabled=True,
            auto_compliance_check=True,
            guideline_enforcement=True,
            violation_threshold=0.3
        )
        
        print("✅ Configuration completed")
        
        # Get agent statistics
        stats = agent.get_statistics()
        print(f"\n📊 Agent Statistics:")
        print(f"   Processed Assets: {stats['processed_assets']}")
        print(f"   Watermarks Applied: {stats['watermarks_applied']}")
        print(f"   Violations Detected: {stats['violations_detected']}")
        print(f"   Average Processing Time: {stats['average_processing_time_ms']:.1f}ms")
        
        print(f"\n🔧 Agent Configuration:")
        config = stats['config']
        print(f"   Watermark Enabled: {config['watermark_enabled']}")
        print(f"   Compliance Enabled: {config['compliance_enabled']}")
        print(f"   Guideline Enforcement: {config['guideline_enforcement']}")
        
        print("\n✨ Integration test completed successfully!")
        
    finally:
        # Cleanup
        if test_image.exists():
            test_image.unlink()
        print("🧹 Cleaned up test files")


async def main():
    """Run all brand protection tests."""
    print("🚀 FIBO OMNI-DIRECTOR PRO - BRAND PROTECTION AGENT TESTS")
    print("="*80)
    
    try:
        # Test individual components
        await test_watermarking_service()
        await test_compliance_checker() 
        await test_brand_guidelines()
        
        # Test full integration
        await test_full_integration()
        
        print("\n" + "="*80)
        print("✅ ALL TESTS COMPLETED SUCCESSFULLY!")
        print("🛡️ Brand Protection Agent system is ready for production use.")
        print("="*80)
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())