"""Integration tests for Brand Guard and Export systems."""

import pytest
import sys
from pathlib import Path
import tempfile
import json
from unittest.mock import Mock, patch

# Add backend to path
backend_path = Path(__file__).parent.parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from app.services.brand_guard import BrandGuard, BrandGuidelines, BrandCheckResult
from app.services.brand_guidelines_loader import BrandGuidelinesLoader
from app.services.export_engine import ExportEngine, ExportAsset, ExportConfig


class TestBrandGuardIntegration:
    """Test Brand Guard system integration."""
    
    def test_brand_guidelines_creation(self):
        """Test creating brand guidelines."""
        guidelines = BrandGuidelines(
            brand_name="Test Brand",
            copyright_text="Test Copyright",
            watermark_enabled=True,
            prohibited_words=["competitor", "unauthorized"],
            required_colors=["#FF0000", "#00FF00"]
        )
        
        guard = BrandGuard(guidelines)
        assert guard.guidelines.brand_name == "Test Brand"
        assert "competitor" in guard.guidelines.prohibited_words
        assert "#FF0000" in guard.guidelines.required_colors
    
    def test_prompt_compliance_pass(self):
        """Test prompt compliance with valid content."""
        guidelines = BrandGuidelines(
            prohibited_words=["competitor"],
            required_colors=["#FF0000"]
        )
        guard = BrandGuard(guidelines)
        
        result = guard.check_prompt_compliance("A beautiful professional image with clean design")
        
        assert result.compliant is True
        assert result.score > 0.8
        assert len(result.violations) == 0
    
    def test_prompt_compliance_fail(self):
        """Test prompt compliance with prohibited content."""
        guidelines = BrandGuidelines(
            prohibited_words=["competitor", "unauthorized"],
            required_colors=["#FF0000"]
        )
        guard = BrandGuard(guidelines)
        
        result = guard.check_prompt_compliance("Image featuring competitor branding and unauthorized content")
        
        assert result.compliant is False
        assert result.score < 0.8
        assert len(result.violations) == 2  # Two prohibited words
        assert any(v.violation_type == "prohibited_content" for v in result.violations)
    
    def test_json_compliance_colors(self):
        """Test JSON compliance with color validation."""
        guidelines = BrandGuidelines(
            prohibited_colors=["#FF0000"],
            required_colors=["#00FF00"]
        )
        guard = BrandGuard(guidelines)
        
        # Test with prohibited color
        bad_json = {
            "color_palette": {
                "primary_colors": ["#FF0000", "#0000FF"]  # Contains prohibited red
            }
        }
        result = guard.check_json_compliance(bad_json)
        assert result.compliant is False
        assert any(v.violation_type == "prohibited_color" for v in result.violations)
        
        # Test with brand-approved colors
        good_json = {
            "color_palette": {
                "primary_colors": ["#00FF00", "#0000FF"]  # Contains required green
            }
        }
        result = guard.check_json_compliance(good_json)
        # Should pass (no prohibited colors, has required color)
        assert len(result.violations) == 0


class TestBrandGuidelinesLoaderIntegration:
    """Test Brand Guidelines Loader system integration."""
    
    def test_guidelines_loading(self):
        """Test loading brand guidelines from JSON."""
        # Create temporary guidelines file
        guidelines_data = {
            "brand_name": "Test Brand",
            "version": "1.0",
            "colors": [
                {
                    "name": "Primary Red",
                    "hex_code": "#FF0000",
                    "rgb": [255, 0, 0],
                    "usage": "primary",
                    "description": "Brand primary color"
                }
            ],
            "typography": [],
            "style": {
                "image_style": "corporate",
                "contrast_requirements": {"text": 4.5},
                "saturation_range": [0.1, 0.8],
                "brightness_range": [0.2, 0.9],
                "aspect_ratios": ["16:9", "1:1"],
                "prohibited_elements": ["watermarks"]
            }
        }
        
        with tempfile.TemporaryDirectory() as temp_dir:
            guidelines_file = Path(temp_dir) / "test_brand.json"
            with open(guidelines_file, 'w') as f:
                json.dump(guidelines_data, f)
            
            loader = BrandGuidelinesLoader(temp_dir)
            guidelines = loader.load_guidelines("test_brand")
            
            assert guidelines is not None
            assert guidelines.brand_name == "Test Brand"
            assert len(guidelines.colors) == 1
            assert guidelines.colors[0].hex_code == "#FF0000"
            assert guidelines.style.image_style == "corporate"
    
    def test_color_validation(self):
        """Test color validation against brand guidelines."""
        guidelines_data = {
            "brand_name": "Test Brand",
            "version": "1.0", 
            "colors": [
                {"name": "Red", "hex_code": "#FF0000", "rgb": [255, 0, 0], "usage": "primary", "description": "Red"},
                {"name": "Blue", "hex_code": "#0000FF", "rgb": [0, 0, 255], "usage": "secondary", "description": "Blue"}
            ],
            "style": {"prohibited_elements": []}
        }
        
        with tempfile.TemporaryDirectory() as temp_dir:
            guidelines_file = Path(temp_dir) / "test_brand.json"
            with open(guidelines_file, 'w') as f:
                json.dump(guidelines_data, f)
            
            loader = BrandGuidelinesLoader(temp_dir)
            guidelines = loader.load_guidelines()
            
            # Test color validation
            results = loader.validate_colors(guidelines, ["#FF0000", "#00FF00", "#0000FF"])
            
            assert results["#FF0000"] is True   # Brand color
            assert results["#0000FF"] is True   # Brand color  
            assert results["#00FF00"] is False  # Non-brand color
    
    def test_negative_prompt_generation(self):
        """Test automatic negative prompt generation."""
        guidelines_data = {
            "brand_name": "Test Brand",
            "version": "1.0",
            "colors": [],
            "style": {
                "prohibited_elements": ["watermarks", "text_overlays", "borders"]
            }
        }
        
        with tempfile.TemporaryDirectory() as temp_dir:
            guidelines_file = Path(temp_dir) / "test_brand.json"
            with open(guidelines_file, 'w') as f:
                json.dump(guidelines_data, f)
            
            loader = BrandGuidelinesLoader(temp_dir)
            guidelines = loader.load_guidelines()
            
            negative_prompt = loader.generate_negative_prompt(guidelines)
            
            assert "watermark" in negative_prompt
            assert "text overlay" in negative_prompt
            assert "border" in negative_prompt
            assert "low quality" in negative_prompt  # Base negatives


class TestExportEngineIntegration:
    """Test Export Engine system integration."""
    
    def test_export_asset_creation(self):
        """Test creating export assets."""
        asset = ExportAsset(
            asset_id="test_001",
            image_url="https://example.com/test.png",
            prompt="Test prompt",
            structured_prompt="test, prompt",
            request_json={"test": "data"},
            metadata={"mode": "test"},
            seed=12345,
            aspect_ratio="1:1"
        )
        
        assert asset.asset_id == "test_001"
        assert asset.seed == 12345
        assert asset.metadata["mode"] == "test"
    
    def test_export_config_creation(self):
        """Test export configuration."""
        config = ExportConfig(
            include_images=True,
            include_json=True,
            create_zip=True,
            apply_watermark=True,
            naming_convention="descriptive",
            export_format="portfolio"
        )
        
        assert config.include_images is True
        assert config.create_zip is True
        assert config.export_format == "portfolio"
    
    @patch('pathlib.Path.exists')
    def test_export_engine_initialization(self, mock_exists):
        """Test export engine initialization."""
        mock_exists.return_value = True
        
        with tempfile.TemporaryDirectory() as temp_dir:
            engine = ExportEngine(temp_dir)
            assert str(engine.export_dir) == temp_dir
    
    def test_filename_generation(self):
        """Test export filename generation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            engine = ExportEngine(temp_dir)
            
            asset = ExportAsset(
                asset_id="test_001",
                image_url="https://example.com/test.png", 
                prompt="A beautiful test image",
                structured_prompt="beautiful, test, image",
                request_json={},
                metadata={},
                seed=12345
            )
            
            config = ExportConfig(naming_convention="descriptive")
            
            # Test filename generation 
            filename = engine._generate_filename(asset, config, 1)
            
            assert "001" in filename  # Index
            assert "12345" in filename  # Seed
            assert "beautiful" in filename.lower() or "test" in filename.lower()  # From prompt


class TestIntegratedWorkflow:
    """Test complete workflow integration."""
    
    def test_brand_guard_to_export_workflow(self):
        """Test complete workflow from brand checking to export."""
        # Create brand guidelines
        guidelines = BrandGuidelines(
            brand_name="Integration Test Brand",
            copyright_text="© Integration Test",
            watermark_enabled=True,
            prohibited_words=["bad", "prohibited"],
            required_colors=["#FF0000"]
        )
        guard = BrandGuard(guidelines)
        
        # Test prompt compliance
        good_prompt = "A professional corporate image with clean design"
        compliance_result = guard.check_prompt_compliance(good_prompt)
        
        assert compliance_result.compliant is True
        
        # Create export asset
        asset = ExportAsset(
            asset_id="integration_test_001",
            image_url="https://example.com/test.png",
            prompt=good_prompt,
            structured_prompt=good_prompt.replace(" ", ", "),
            request_json={"prompt": good_prompt, "compliant": True},
            metadata={
                "brand_compliance": {
                    "score": compliance_result.score,
                    "violations": len(compliance_result.violations)
                }
            },
            seed=98765
        )
        
        # Configure export with brand protection
        config = ExportConfig(
            apply_watermark=True,  # Enable brand protection
            include_metadata=True,
            naming_convention="descriptive"
        )
        
        # Verify asset has compliance metadata
        assert asset.metadata["brand_compliance"]["score"] == compliance_result.score
        assert asset.metadata["brand_compliance"]["violations"] == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])