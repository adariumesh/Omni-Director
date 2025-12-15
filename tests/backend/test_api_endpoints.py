"""API endpoint tests for Brand Guard and Export routes."""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import json
from fastapi.testclient import TestClient

# Add backend to path
backend_path = Path(__file__).parent.parent.parent / "backend"
sys.path.insert(0, str(backend_path))


class TestHealthEndpoint:
    """Test health check endpoint."""
    
    def test_health_endpoint_import(self):
        """Test that health endpoint can be imported."""
        from app.main import health_check
        assert health_check is not None
    
    @patch('app.main.get_db')
    @patch('app.main.settings')
    def test_health_endpoint_healthy(self, mock_settings, mock_get_db):
        """Test health endpoint with healthy services."""
        # Mock database connection
        mock_db = Mock()
        mock_db.execute.return_value = None
        mock_get_db.return_value = [mock_db]
        
        # Mock settings
        mock_settings.bria_api_key = "valid_api_key"
        mock_settings.environment = "test"
        
        from app.main import health_check
        import asyncio
        
        result = asyncio.run(health_check())
        
        assert result["status"] == "healthy"
        assert result["database"] == "healthy"
        assert result["bria_api"] == "configured"
        assert "timestamp" in result
        assert "version" in result
    
    @patch('app.main.get_db')
    @patch('app.main.settings')
    def test_health_endpoint_degraded(self, mock_settings, mock_get_db):
        """Test health endpoint with degraded services."""
        # Mock database connection failure
        mock_db = Mock()
        mock_db.execute.side_effect = Exception("DB connection failed")
        mock_get_db.return_value = [mock_db]
        
        # Mock missing API key
        mock_settings.bria_api_key = None
        mock_settings.environment = "test"
        
        from app.main import health_check
        import asyncio
        
        result = asyncio.run(health_check())
        
        assert result["status"] == "degraded"
        assert result["database"] == "unhealthy"
        assert result["bria_api"] == "not_configured"


class TestBrandExportAPIEndpoints:
    """Test Brand Export API endpoints."""
    
    def test_brand_export_routes_import(self):
        """Test that brand export routes can be imported."""
        from app.routes.brand_export_routes import router
        assert router is not None
    
    @patch('app.routes.brand_export_routes.brand_loader')
    def test_get_brand_guidelines_default(self, mock_loader):
        """Test GET /api/v1/brand/guidelines with no guidelines."""
        mock_loader.load_guidelines.return_value = None
        
        from app.routes.brand_export_routes import get_brand_guidelines
        import asyncio
        
        result = asyncio.run(get_brand_guidelines())
        
        assert result["brand_name"] == "FIBO Omni-Director"
        assert result["status"] == "default"
        assert result["version"] == "1.0"
        assert isinstance(result["prohibited_words"], list)
    
    @patch('app.routes.brand_export_routes.brand_loader')
    def test_get_brand_guidelines_loaded(self, mock_loader):
        """Test GET /api/v1/brand/guidelines with loaded guidelines."""
        # Mock loaded guidelines
        mock_guidelines = Mock()
        mock_guidelines.brand_name = "Test Brand"
        mock_guidelines.version = "2.0"
        mock_guidelines.colors = [
            Mock(name="Red", hex_code="#FF0000", usage="primary", description="Test red"),
            Mock(name="Blue", hex_code="#0000FF", usage="secondary", description="Test blue")
        ]
        mock_guidelines.style = Mock()
        mock_guidelines.style.image_style = "modern"
        mock_guidelines.style.aspect_ratios = ["16:9", "1:1"]
        mock_guidelines.style.prohibited_elements = ["watermarks"]
        
        mock_loader.load_guidelines.return_value = mock_guidelines
        
        from app.routes.brand_export_routes import get_brand_guidelines
        import asyncio
        
        result = asyncio.run(get_brand_guidelines())
        
        assert result["brand_name"] == "Test Brand"
        assert result["status"] == "loaded"
        assert result["version"] == "2.0"
        assert len(result["colors"]) == 2
        assert result["style"]["image_style"] == "modern"
    
    @patch('pathlib.Path.mkdir')
    @patch('builtins.open')
    @patch('json.dump')
    def test_update_brand_guidelines(self, mock_json_dump, mock_open, mock_mkdir):
        """Test POST /api/v1/brand/guidelines."""
        from app.routes.brand_export_routes import update_brand_guidelines, BrandGuidelinesUpdateRequest
        import asyncio
        
        # Mock file operations
        mock_open.return_value.__enter__.return_value = Mock()
        
        request = BrandGuidelinesUpdateRequest(
            brand_name="Test Brand",
            copyright_text="Test Copyright",
            watermark_enabled=True,
            logo_position="bottom_right",
            logo_opacity=0.8,
            prohibited_words=["test", "prohibited"],
            prohibited_colors=["#FF0000"],
            required_colors=["#00FF00"],
            min_resolution=[1024, 1024]
        )
        
        result = asyncio.run(update_brand_guidelines(request))
        
        assert result["success"] is True
        assert "Brand guidelines updated successfully" in result["message"]
        assert "guideline_id" in result
        assert "timestamp" in result
        
        # Verify file operations were called
        mock_mkdir.assert_called()
        mock_json_dump.assert_called()
    
    @patch('app.routes.brand_export_routes.brand_loader')
    def test_brand_compliance_check_prompt(self, mock_loader):
        """Test POST /api/v1/brand/check with prompt."""
        # Mock guidelines
        mock_guidelines_spec = Mock()
        mock_guidelines_spec.brand_name = "Test Brand"
        mock_guidelines_spec.colors = [
            Mock(hex_code="#FF0000", usage="primary")
        ]
        mock_loader.load_guidelines.return_value = mock_guidelines_spec
        
        from app.routes.brand_export_routes import check_brand_compliance, BrandComplianceCheckRequest
        import asyncio
        
        request = BrandComplianceCheckRequest(
            prompt="A beautiful professional image with clean design"
        )
        
        result = asyncio.run(check_brand_compliance(request))
        
        assert "compliant" in result
        assert "score" in result
        assert "violations" in result
        assert "suggestions" in result
        assert isinstance(result["violations"], list)
        assert isinstance(result["suggestions"], list)
    
    @patch('app.routes.brand_export_routes.brand_loader')
    def test_brand_compliance_check_json(self, mock_loader):
        """Test POST /api/v1/brand/check with JSON."""
        # Mock guidelines
        mock_guidelines_spec = Mock()
        mock_guidelines_spec.brand_name = "Test Brand"
        mock_guidelines_spec.colors = [
            Mock(hex_code="#FF0000", usage="primary")
        ]
        mock_loader.load_guidelines.return_value = mock_guidelines_spec
        
        from app.routes.brand_export_routes import check_brand_compliance, BrandComplianceCheckRequest
        import asyncio
        
        request = BrandComplianceCheckRequest(
            request_json={
                "color_palette": {
                    "primary_colors": ["#FF0000", "#00FF00"]
                },
                "style": "corporate professional"
            }
        )
        
        result = asyncio.run(check_brand_compliance(request))
        
        assert "compliant" in result
        assert "score" in result
        assert "violations" in result
        assert isinstance(result["violations"], list)
    
    @patch('app.routes.brand_export_routes.export_engine')
    def test_export_assets_missing_assets(self, mock_export_engine):
        """Test POST /api/v1/export with missing assets."""
        from app.routes.brand_export_routes import export_assets, ExportRequest
        from sqlalchemy.orm import Session
        import asyncio
        
        # Mock database session with no assets
        mock_db = Mock(spec=Session)
        mock_db.query.return_value.filter.return_value.all.return_value = []
        
        request = ExportRequest(
            asset_ids=["nonexistent_001", "nonexistent_002"],
            format_type="portfolio"
        )
        
        with pytest.raises(Exception):  # Should raise HTTPException for missing assets
            asyncio.run(export_assets(request, mock_db))


class TestIntegrationAPIs:
    """Test API integration scenarios."""
    
    @patch('app.routes.brand_export_routes.brand_loader')
    def test_guidelines_to_compliance_workflow(self, mock_loader):
        """Test workflow from loading guidelines to checking compliance."""
        # Setup mock guidelines
        mock_guidelines_spec = Mock()
        mock_guidelines_spec.brand_name = "Workflow Test Brand"
        mock_guidelines_spec.colors = [
            Mock(hex_code="#FF0000", usage="primary"),
            Mock(hex_code="#00FF00", usage="secondary")
        ]
        mock_loader.load_guidelines.return_value = mock_guidelines_spec
        
        from app.routes.brand_export_routes import get_brand_guidelines, check_brand_compliance, BrandComplianceCheckRequest
        import asyncio
        
        # Get guidelines
        guidelines_result = asyncio.run(get_brand_guidelines())
        assert guidelines_result["brand_name"] == "Workflow Test Brand"
        
        # Use guidelines to check compliance
        compliance_request = BrandComplianceCheckRequest(
            prompt="A professional image using our brand colors"
        )
        compliance_result = asyncio.run(check_brand_compliance(compliance_request))
        
        assert "compliant" in compliance_result
        assert "score" in compliance_result
    
    def test_api_error_handling(self):
        """Test API error handling for invalid requests."""
        from app.routes.brand_export_routes import BrandComplianceCheckRequest
        
        # Test invalid request (no prompt or JSON)
        invalid_request = BrandComplianceCheckRequest()
        assert invalid_request.prompt is None
        assert invalid_request.request_json is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])