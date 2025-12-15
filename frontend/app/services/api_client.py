"""HTTP client for backend API communication."""

import logging
from typing import Any

import httpx

from app.config import config

logger = logging.getLogger(__name__)


class APIError(Exception):
    """Exception raised when API call fails."""

    def __init__(self, status_code: int, message: str) -> None:
        """Initialize APIError.

        Args:
            status_code: HTTP status code.
            message: Error message.
        """
        self.status_code = status_code
        self.message = message
        super().__init__(f"API Error {status_code}: {message}")


class APIClient:
    """HTTP client for communicating with backend API."""

    def __init__(self, base_url: str | None = None) -> None:
        """Initialize API client.

        Args:
            base_url: Backend API URL. Defaults to config value.
        """
        self.base_url = base_url or config.backend_url
        self.timeout = 120.0  # Long timeout for image generation

    def _make_request(
        self,
        method: str,
        endpoint: str,
        json: dict | None = None,
        params: dict | None = None,
    ) -> dict[str, Any]:
        """Make HTTP request to backend.

        Args:
            method: HTTP method (GET, POST, etc.).
            endpoint: API endpoint path.
            json: Optional JSON body.
            params: Optional query parameters.

        Returns:
            Response JSON as dict.

        Raises:
            APIError: If request fails.
        """
        url = f"{self.base_url}{endpoint}"

        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.request(
                    method=method,
                    url=url,
                    json=json,
                    params=params,
                )

                if response.status_code >= 400:
                    error_data = response.json() if response.content else {}
                    message = error_data.get("detail", response.text)
                    raise APIError(response.status_code, message)

                return response.json()

        except httpx.TimeoutException as e:
            logger.error(f"Request timeout: {e}")
            raise APIError(408, "Request timed out") from e

        except httpx.RequestError as e:
            logger.error(f"Request error: {e}")
            raise APIError(500, f"Connection failed: {str(e)}") from e

    # ==================== Health ====================

    def health_check(self) -> dict[str, Any]:
        """Check backend health.

        Returns:
            Health status dict.
        """
        return self._make_request("GET", "/api/v1/health")

    # ==================== Generation ====================

    def generate_image(
        self,
        prompt: str,
        seed: int | None = None,
        aspect_ratio: str = "1:1",
        project_id: str | None = None,
    ) -> dict[str, Any]:
        """Generate a single image.

        Args:
            prompt: Image description.
            seed: Optional seed for determinism.
            aspect_ratio: Image aspect ratio.
            project_id: Optional project to save to.

        Returns:
            Generation response with image URL.
        """
        payload = {
            "prompt": prompt,
            "aspect_ratio": aspect_ratio,
        }

        if seed is not None:
            payload["seed"] = seed
        if project_id is not None:
            payload["project_id"] = project_id

        return self._make_request("POST", "/api/v1/generate", json=payload)

    def generate_matrix(
        self,
        base_prompt: str,
        seed: int | None = None,
        aspect_ratio: str = "1:1",
        project_id: str | None = None,
        camera_angles: list[str] | None = None,
        lighting_styles: list[str] | None = None,
    ) -> dict[str, Any]:
        """Generate 3x3 deterministic matrix.

        Args:
            base_prompt: Base image description.
            seed: Optional seed for determinism.
            aspect_ratio: Image aspect ratio.
            project_id: Optional project to save to.
            camera_angles: Optional custom camera angles.
            lighting_styles: Optional custom lighting styles.

        Returns:
            Matrix response with all 9 cells.
        """
        payload = {
            "base_prompt": base_prompt,
            "aspect_ratio": aspect_ratio,
        }

        if seed is not None:
            payload["seed"] = seed
        if project_id is not None:
            payload["project_id"] = project_id
        if camera_angles is not None:
            payload["camera_angles"] = camera_angles
        if lighting_styles is not None:
            payload["lighting_styles"] = lighting_styles

        return self._make_request("POST", "/api/v1/matrix", json=payload)

    def mutate_cell(
        self,
        asset_id: str,
        mutations: dict[str, str],
    ) -> dict[str, Any]:
        """Mutate a cell with new parameters.

        Args:
            asset_id: ID of asset to mutate.
            mutations: Dict of parameter changes.

        Returns:
            Generation response with mutated image.
        """
        payload = {
            "asset_id": asset_id,
            "mutations": mutations,
        }

        return self._make_request("POST", "/api/v1/mutate", json=payload)

    # ==================== Aspect Ratios ====================

    def get_aspect_ratios(self) -> list[str]:
        """Get list of valid aspect ratios.

        Returns:
            List of aspect ratio strings.
        """
        response = self._make_request("GET", "/api/v1/aspect-ratios")
        return response.get("aspect_ratios", [])

    # ==================== FIBO Advanced ====================

    def fibo_generate(
        self,
        natural_prompt: str,
        seed: int | None = None,
        aspect_ratio: str = "1:1",
        project_id: str | None = None,
    ) -> dict[str, Any]:
        """FIBO Generate mode: Natural language → Advanced JSON → Image.

        Args:
            natural_prompt: Natural language description.
            seed: Optional seed for determinism.
            aspect_ratio: Image aspect ratio.
            project_id: Optional project to save to.

        Returns:
            FIBO advanced response with images and JSON.
        """
        payload = {
            "natural_prompt": natural_prompt,
            "aspect_ratio": aspect_ratio,
        }

        if seed is not None:
            payload["seed"] = seed
        if project_id is not None:
            payload["project_id"] = project_id

        return self._make_request("POST", "/api/v1/fibo/generate", json=payload)

    def fibo_refine(
        self,
        asset_id: str,
        modification: str,
        project_id: str | None = None,
    ) -> dict[str, Any]:
        """FIBO Refine mode: Modify specific attributes without breaking scene.

        Args:
            asset_id: ID of asset to refine.
            modification: What to change.
            project_id: Optional project to save to.

        Returns:
            FIBO advanced response with refined images.
        """
        payload = {
            "asset_id": asset_id,
            "modification": modification,
        }

        if project_id is not None:
            payload["project_id"] = project_id

        return self._make_request("POST", "/api/v1/fibo/refine", json=payload)

    def fibo_inspire(
        self,
        reference_asset_id: str,
        subject_change: str,
        seed: int | None = None,
        aspect_ratio: str = "1:1",
        project_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """FIBO Inspire mode: Generate variations maintaining style consistency.

        Args:
            reference_asset_id: Reference asset for style.
            subject_change: New subject description.
            seed: Optional seed for determinism.
            aspect_ratio: Image aspect ratio.
            project_id: Optional project to save to.

        Returns:
            List of FIBO advanced responses with inspired variations.
        """
        payload = {
            "reference_asset_id": reference_asset_id,
            "subject_change": subject_change,
            "aspect_ratio": aspect_ratio,
        }

        if seed is not None:
            payload["seed"] = seed
        if project_id is not None:
            payload["project_id"] = project_id

        return self._make_request("POST", "/api/v1/fibo/inspire", json=payload)

    def fibo_advanced_direct(
        self,
        advanced_request: dict[str, Any],
    ) -> dict[str, Any]:
        """Direct advanced FIBO generation with full parameter control.

        Args:
            advanced_request: Complete FIBO advanced request JSON.

        Returns:
            FIBO advanced response with generated images.
        """
        return self._make_request("POST", "/api/v1/fibo/advanced", json=advanced_request)

    def get_fibo_modes(self) -> dict[str, Any]:
        """Get available FIBO generation modes.

        Returns:
            Dict with available modes and descriptions.
        """
        return self._make_request("GET", "/api/v1/fibo/modes")

    # ==================== Root ====================

    def get_info(self) -> dict[str, Any]:
        """Get API info.

        Returns:
            API info dict.
        """
        return self._make_request("GET", "/")
