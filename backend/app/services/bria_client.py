"""Bria API client for FIBO image generation."""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

import httpx

from app.config import settings
from app.services.schema_validator import FIBOAdvancedRequest

logger = logging.getLogger(__name__)


class BriaAPIError(Exception):
    """Exception raised when Bria API returns an error."""

    def __init__(
        self,
        status_code: int,
        message: str,
        request_id: str | None = None,
    ) -> None:
        """Initialize BriaAPIError.

        Args:
            status_code: HTTP status code from API.
            message: Error message from API.
            request_id: Optional request ID for debugging.
        """
        self.status_code = status_code
        self.message = message
        self.request_id = request_id
        super().__init__(f"Bria API Error {status_code}: {message}")


@dataclass
class ImageResult:
    """Result from a successful image generation."""

    url: str
    seed: int
    prompt: str
    aspect_ratio: str
    created_at: datetime
    local_path: Optional[str] = None
    file_id: Optional[str] = None
    thumbnail_path: Optional[str] = None


# Valid aspect ratios supported by Bria API
VALID_ASPECT_RATIOS = [
    "1:1",
    "2:3",
    "3:2",
    "3:4",
    "4:3",
    "4:5",
    "5:4",
    "9:16",
    "16:9",
]


class BriaClient:
    """Client for interacting with Bria FIBO API."""

    def __init__(self, api_key: str | None = None, auto_download: bool = True) -> None:
        """Initialize Bria client.

        Args:
            api_key: Bria API key. If None, uses settings.
            auto_download: Whether to automatically download and store generated images.
        """
        self.api_key = api_key or settings.bria_api_key
        self.base_url = settings.bria_api_base_url
        self.timeout = 60.0  # Seconds
        self.auto_download = auto_download

        if not self.api_key:
            logger.warning("Bria API key not configured")
        
        # Initialize file storage if auto_download enabled
        if self.auto_download:
            try:
                from app.services.file_storage import get_file_storage
                self.file_storage = get_file_storage()
                logger.info("✅ File storage enabled for image downloads")
            except Exception as e:
                logger.warning(f"⚠️ File storage unavailable: {e}")
                self.auto_download = False
                self.file_storage = None

    def _get_headers(self) -> dict[str, str]:
        """Get HTTP headers for API requests.

        Returns:
            Headers dict with authentication.
        """
        return {
            "api_token": self.api_key,
            "Content-Type": "application/json",
        }

    def generate(
        self,
        prompt: str,
        seed: int | None = None,
        aspect_ratio: str = "1:1",
        num_results: int = 1,
        sync: bool = True,
    ) -> list[ImageResult]:
        """Generate images using Bria FIBO API.

        Args:
            prompt: Text description of desired image.
            seed: Optional seed for deterministic generation.
            aspect_ratio: Image aspect ratio (default "1:1").
            num_results: Number of images to generate (1-4).
            sync: Whether to wait for results (default True).

        Returns:
            List of ImageResult objects.

        Raises:
            BriaAPIError: If API call fails.
            ValueError: If parameters are invalid.
        """
        # Validate parameters
        if not prompt or not prompt.strip():
            raise ValueError("Prompt cannot be empty")

        if aspect_ratio not in VALID_ASPECT_RATIOS:
            raise ValueError(
                f"Invalid aspect ratio: {aspect_ratio}. "
                f"Valid options: {VALID_ASPECT_RATIOS}"
            )

        if num_results < 1 or num_results > 4:
            raise ValueError("num_results must be between 1 and 4")

        if seed is not None and (seed < 0 or seed > 2147483647):
            raise ValueError("Seed must be between 0 and 2147483647")

        # Build request payload
        payload: dict = {
            "prompt": prompt.strip(),
            "num_results": num_results,
            "aspect_ratio": aspect_ratio,
            "sync": sync,
        }

        if seed is not None:
            payload["seed"] = seed

        logger.info(f"Generating image with prompt: {prompt[:50]}...")
        logger.debug(f"Full payload: {payload}")

        # Make API request
        endpoint = f"{self.base_url}/text-to-image/base/2.3"

        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(
                    endpoint,
                    json=payload,
                    headers=self._get_headers(),
                )

                # Handle errors
                if response.status_code != 200:
                    # Try to parse JSON, fallback to text
                    try:
                        error_data = response.json()
                        error_message = error_data.get("message", str(error_data))
                        request_id = error_data.get("request_id")
                    except Exception:
                        error_message = response.text
                        request_id = None

                    logger.error(
                        f"Bria API error: {response.status_code} - {error_message}"
                    )

                    # Specific message for unauthorized
                    if response.status_code == 401:
                        error_message = "Bria API key is missing or invalid. Please check your .env and restart the backend."

                    raise BriaAPIError(
                        status_code=response.status_code,
                        message=error_message,
                        request_id=request_id,
                    )

                # Parse successful response
                data = response.json()
                results = []

                for item in data.get("result", []):
                    urls = item.get("urls", [])
                    result_seed = item.get("seed", seed or 0)

                    for url in urls:
                        # Create base result
                        result = ImageResult(
                            url=url,
                            seed=result_seed,
                            prompt=prompt,
                            aspect_ratio=aspect_ratio,
                            created_at=datetime.utcnow(),
                        )
                        
                        # Download and store image if enabled
                        if self.auto_download and self.file_storage:
                            try:
                                stored_file = self.file_storage.download_image_from_url(url)
                                result.local_path = str(stored_file.stored_path)
                                result.file_id = stored_file.file_id
                                
                                # Create thumbnail
                                thumbnail_path = self.file_storage.create_thumbnail(stored_file)
                                if thumbnail_path:
                                    result.thumbnail_path = str(thumbnail_path)
                                
                                logger.info(f"✅ Downloaded and stored image: {stored_file.file_id}")
                                
                            except Exception as e:
                                logger.warning(f"⚠️ Failed to download image {url}: {e}")
                                # Continue with just the URL - don't fail the whole request
                        
                        results.append(result)

                logger.info(f"Successfully generated {len(results)} image(s)")
                return results

        except httpx.TimeoutException as e:
            logger.error(f"Bria API timeout: {e}")
            raise BriaAPIError(
                status_code=408,
                message="Request timed out",
            ) from e

        except httpx.RequestError as e:
            logger.error(f"Bria API request error: {e}")
            raise BriaAPIError(
                status_code=500,
                message=f"Request failed: {str(e)}",
            ) from e

    def generate_with_locked_seed(
        self,
        prompt: str,
        seed: int,
        aspect_ratio: str = "1:1",
    ) -> ImageResult:
        """Generate a single image with a locked seed.

        This is a convenience method for deterministic generation.

        Args:
            prompt: Text description of desired image.
            seed: Seed for deterministic generation.
            aspect_ratio: Image aspect ratio (default "1:1").

        Returns:
            Single ImageResult.

        Raises:
            BriaAPIError: If API call fails.
            ValueError: If parameters are invalid.
        """
        results = self.generate(
            prompt=prompt,
            seed=seed,
            aspect_ratio=aspect_ratio,
            num_results=1,
            sync=True,
        )

        if not results:
            raise BriaAPIError(
                status_code=500,
                message="No images returned from API",
            )

        return results[0]

    def test_connection(self) -> bool:
        """Test API connectivity.

        Returns:
            True if API is reachable and authenticated.

        Raises:
            BriaAPIError: If connection test fails.
        """
        try:
            # Make a minimal request to test authentication
            # Using a simple prompt that should always work
            self.generate(
                prompt="test",
                num_results=1,
                sync=True,
            )
            return True

        except BriaAPIError as e:
            if e.status_code == 401:
                logger.error("Invalid API key")
            raise

    def generate_advanced(self, request: FIBOAdvancedRequest) -> list[ImageResult]:
        """Generate images using advanced FIBO parameters.

        Args:
            request: Advanced FIBO request with professional parameters.

        Returns:
            List of generated ImageResult objects.

        Raises:
            BriaAPIError: If generation fails.
        """
        # Convert advanced request to structured prompt
        structured_prompt = request.to_structured_prompt()
        
        logger.info(f"Generating with advanced FIBO parameters: {request.subject}")
        logger.debug(f"Structured prompt: {structured_prompt}")
        
        # Use the existing generate method with the structured prompt
        return self.generate(
            prompt=structured_prompt,
            num_results=1,
            aspect_ratio=request.aspect_ratio,
            seed=request.seed,
            sync=True,
        )
