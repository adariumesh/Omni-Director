"""VLM-powered translation from natural language to FIBO JSON schemas."""

import json
import logging
from typing import Optional

import httpx
from pydantic import BaseModel, Field

from app.config import settings
from app.services.schema_validator import (
    FIBOAdvancedRequest,
    CameraSettings,
    LightingSettings,
    CompositionSettings,
    ColorPalette,
)

logger = logging.getLogger(__name__)


class VLMTranslatorError(Exception):
    """Exception raised when VLM translation fails."""

    def __init__(self, message: str, original_error: Exception | None = None):
        self.message = message
        self.original_error = original_error
        super().__init__(message)


class VLMTranslator:
    """Translates natural language to structured FIBO JSON."""

    def __init__(self, openai_api_key: Optional[str] = None):
        """Initialize VLM translator.
        
        Args:
            openai_api_key: OpenAI API key. If None, tries environment variable.
        """
        self.api_key = openai_api_key or settings.openai_api_key
        if not self.api_key:
            raise VLMTranslatorError(
                "OpenAI API key not provided. Set OPENAI_API_KEY environment variable."
            )
        
        self.base_url = "https://api.openai.com/v1"
        self.timeout = 30.0

    def _get_headers(self) -> dict[str, str]:
        """Get headers for OpenAI API requests."""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _get_system_prompt(self) -> str:
        """Get the system prompt for FIBO parameter extraction."""
        return """You are a professional photographer's AI assistant. Your job is to convert casual natural language prompts into detailed JSON schemas for FIBO image generation.

FIBO uses structured parameters for precise control:

Camera Settings:
- angle: front_view, three_quarter_view, side_view, back_view, top_down, low_angle, high_angle, eye_level
- focal_length: 14mm, 24mm, 35mm, 50mm, 85mm, 105mm, 135mm, 200mm  
- depth_of_field: shallow, medium, deep, hyperfocal
- distance: close_up, medium_shot, wide_shot

Lighting Settings:
- setup: studio_three_point, rembrandt, split_lighting, butterfly, loop_lighting, rim_lighting, natural_window, golden_hour, blue_hour, dramatic_side, soft_diffused, hard_directional
- temperature: tungsten_3200k, daylight_5600k, cloudy_6500k, shade_7500k, warm_2700k, cool_8000k
- intensity: low, medium, high
- direction: front, front_left_45, front_right_45, side_left, side_right, back_left, back_right

Composition:
- rule: rule_of_thirds, golden_ratio, symmetrical, asymmetrical, leading_lines, frame_in_frame, fill_frame, negative_space
- balance: symmetrical, asymmetrical
- negative_space: minimal, moderate, extensive

Colors:
- primary_colors: Array of color names (e.g., ["gold", "black", "white"])
- accent_colors: Array of accent colors
- temperature: very_warm, warm, neutral, cool, very_cool
- saturation: desaturated, natural, vibrant, oversaturated

Background: white_seamless, black_seamless, gradient_neutral, textured_wall, wooden_surface, marble_surface, fabric_backdrop, outdoor_natural, studio_cyc, transparent

Style: professional_photography, portrait, fashion, product, architectural, lifestyle, fine_art

Mood: professional, dramatic, elegant, modern, vintage, minimalist, luxury, industrial, organic, futuristic

Always respond with valid JSON only, no explanations. Extract and infer professional photography parameters from the input."""

    def translate_to_advanced_request(self, natural_prompt: str) -> FIBOAdvancedRequest:
        """Translate natural language to FIBOAdvancedRequest.

        Args:
            natural_prompt: Natural language description.

        Returns:
            FIBOAdvancedRequest with extracted parameters.

        Raises:
            VLMTranslatorError: If translation fails.
        """
        logger.info(f"Translating prompt: {natural_prompt}")
        
        # Create user prompt with example
        user_prompt = f"""Convert this natural language prompt to a FIBO JSON schema:

"{natural_prompt}"

Respond with JSON only in this exact format:
{{
  "subject": "extracted main subject",
  "camera": {{
    "angle": "appropriate_angle",
    "focal_length": "appropriate_mm",
    "depth_of_field": "shallow/medium/deep",
    "distance": "close_up/medium_shot/wide_shot"
  }},
  "lighting": {{
    "setup": "appropriate_setup",
    "temperature": "appropriate_temperature",
    "intensity": "low/medium/high",
    "direction": "appropriate_direction"
  }},
  "composition": {{
    "rule": "rule_of_thirds",
    "balance": "asymmetrical", 
    "negative_space": "minimal"
  }},
  "color_palette": {{
    "primary_colors": ["color1", "color2"],
    "accent_colors": ["accent1"],
    "temperature": "warm/neutral/cool",
    "saturation": "natural"
  }},
  "background": "appropriate_background",
  "style": "professional_photography",
  "mood": "appropriate_mood",
  "aspect_ratio": "1:1"
}}"""

        # Make OpenAI API request
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(
                    f"{self.base_url}/chat/completions",
                    headers=self._get_headers(),
                    json={
                        "model": "gpt-4",
                        "messages": [
                            {"role": "system", "content": self._get_system_prompt()},
                            {"role": "user", "content": user_prompt}
                        ],
                        "temperature": 0.3,
                        "max_tokens": 1000,
                    }
                )

                if response.status_code != 200:
                    error_msg = f"OpenAI API error {response.status_code}: {response.text}"
                    logger.error(error_msg)
                    raise VLMTranslatorError(error_msg)

                # Parse response
                data = response.json()
                content = data["choices"][0]["message"]["content"].strip()
                
                # Clean JSON (remove code blocks if present)
                if content.startswith("```"):
                    content = content.split("\\n", 1)[1]
                    content = content.rsplit("\\n```", 1)[0]
                
                # Parse JSON
                try:
                    parsed_json = json.loads(content)
                    logger.debug(f"Parsed JSON: {parsed_json}")
                    
                    # Create FIBOAdvancedRequest from parsed JSON
                    return FIBOAdvancedRequest(**parsed_json)
                    
                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON from VLM: {content}")
                    raise VLMTranslatorError(f"VLM returned invalid JSON: {e}")
                    
                except Exception as e:
                    logger.error(f"Failed to create FIBOAdvancedRequest: {e}")
                    raise VLMTranslatorError(f"Schema validation failed: {e}")

        except httpx.TimeoutException as e:
            logger.error("OpenAI API timeout")
            raise VLMTranslatorError("Translation request timed out") from e

        except httpx.RequestError as e:
            logger.error(f"OpenAI API request error: {e}")
            raise VLMTranslatorError(f"API request failed: {e}") from e

    def translate_simple(self, natural_prompt: str) -> dict:
        """Simple translation that returns raw JSON dict.

        Args:
            natural_prompt: Natural language description.

        Returns:
            Dictionary with extracted parameters.

        Raises:
            VLMTranslatorError: If translation fails.
        """
        advanced_request = self.translate_to_advanced_request(natural_prompt)
        return advanced_request.dict()

    def enhance_existing_request(
        self, 
        request: FIBOAdvancedRequest, 
        enhancement: str
    ) -> FIBOAdvancedRequest:
        """Enhance an existing request with additional instructions.

        Args:
            request: Existing FIBO request.
            enhancement: Additional enhancement instruction.

        Returns:
            Enhanced FIBOAdvancedRequest.

        Raises:
            VLMTranslatorError: If enhancement fails.
        """
        # Convert existing request to prompt
        current_prompt = f"Subject: {request.subject}, using {request.lighting.setup} lighting, {request.camera.angle} camera angle, {request.mood} mood"
        
        # Create enhancement prompt
        enhancement_prompt = f"Enhance this photography setup: '{current_prompt}' by {enhancement}"
        
        # Translate enhanced prompt
        return self.translate_to_advanced_request(enhancement_prompt)


def get_vlm_translator() -> VLMTranslator:
    """Get a VLM translator instance.
    
    Returns:
        VLMTranslator instance.
    """
    return VLMTranslator()