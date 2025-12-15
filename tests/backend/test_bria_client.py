"""Tests for Bria API client."""

import pytest
from unittest.mock import MagicMock, patch

from backend.app.services.bria_client import (
    BriaAPIError,
    BriaClient,
    ImageResult,
    VALID_ASPECT_RATIOS,
)


class TestBriaClientValidation:
    """Test input validation for BriaClient."""

    def test_empty_prompt_raises_value_error(self) -> None:
        """Verify empty prompt raises ValueError."""
        client = BriaClient(api_key="test_key")
        
        with pytest.raises(ValueError, match="Prompt cannot be empty"):
            client.generate(prompt="", seed=123)

    def test_whitespace_only_prompt_raises_value_error(self) -> None:
        """Verify whitespace-only prompt raises ValueError."""
        client = BriaClient(api_key="test_key")
        
        with pytest.raises(ValueError, match="Prompt cannot be empty"):
            client.generate(prompt="   ", seed=123)

    def test_invalid_aspect_ratio_raises_value_error(self) -> None:
        """Verify invalid aspect ratio raises ValueError."""
        client = BriaClient(api_key="test_key")
        
        with pytest.raises(ValueError, match="Invalid aspect ratio"):
            client.generate(prompt="test", aspect_ratio="1:3")

    def test_negative_seed_raises_value_error(self) -> None:
        """Verify negative seed raises ValueError."""
        client = BriaClient(api_key="test_key")
        
        with pytest.raises(ValueError, match="Seed must be between"):
            client.generate(prompt="test", seed=-1)

    def test_seed_too_large_raises_value_error(self) -> None:
        """Verify seed > max raises ValueError."""
        client = BriaClient(api_key="test_key")
        
        with pytest.raises(ValueError, match="Seed must be between"):
            client.generate(prompt="test", seed=2147483648)

    def test_num_results_out_of_range_raises_value_error(self) -> None:
        """Verify num_results out of range raises ValueError."""
        client = BriaClient(api_key="test_key")
        
        with pytest.raises(ValueError, match="num_results must be between"):
            client.generate(prompt="test", num_results=5)

    @pytest.mark.parametrize("aspect_ratio", VALID_ASPECT_RATIOS)
    def test_valid_aspect_ratios_accepted(self, aspect_ratio: str, mock_bria_client) -> None:
        """Verify all valid aspect ratios are accepted."""
        client = BriaClient(api_key="test_key")
        
        # Should not raise
        try:
            client.generate(prompt="test", aspect_ratio=aspect_ratio)
        except BriaAPIError:
            pass  # API errors are fine, we're testing validation


class TestBriaClientGeneration:
    """Test image generation functionality."""

    def test_generate_returns_image_result(self, mock_bria_client, mock_bria_response) -> None:
        """Verify generate returns ImageResult objects."""
        client = BriaClient(api_key="test_key")
        
        results = client.generate(prompt="test prompt", seed=12345)
        
        assert len(results) == 1
        assert isinstance(results[0], ImageResult)
        assert results[0].url == "https://example.com/image.png"
        assert results[0].seed == 12345

    def test_generate_with_locked_seed_returns_single_result(
        self, mock_bria_client, mock_bria_response
    ) -> None:
        """Verify generate_with_locked_seed returns single result."""
        client = BriaClient(api_key="test_key")
        
        result = client.generate_with_locked_seed(
            prompt="test prompt",
            seed=12345,
            aspect_ratio="1:1",
        )
        
        assert isinstance(result, ImageResult)
        assert result.seed == 12345


class TestBriaAPIError:
    """Test BriaAPIError exception."""

    def test_error_contains_status_code(self) -> None:
        """Verify error contains status code."""
        error = BriaAPIError(status_code=401, message="Unauthorized")
        
        assert error.status_code == 401
        assert "401" in str(error)

    def test_error_contains_message(self) -> None:
        """Verify error contains message."""
        error = BriaAPIError(status_code=401, message="Unauthorized")
        
        assert error.message == "Unauthorized"
        assert "Unauthorized" in str(error)

    def test_error_contains_request_id(self) -> None:
        """Verify error can contain request ID."""
        error = BriaAPIError(
            status_code=500,
            message="Server error",
            request_id="req-123",
        )
        
        assert error.request_id == "req-123"
