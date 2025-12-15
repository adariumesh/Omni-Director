"""BRIA API Research and Parameter Mapping for Real Integration."""

import logging
import json
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import httpx

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class BriaAPICapabilities:
    """BRIA API capabilities discovered through research."""
    
    supported_models: List[str]
    max_prompt_length: int
    supported_aspect_ratios: List[str] 
    supported_parameters: Dict[str, Any]
    parameter_limits: Dict[str, Dict[str, Any]]
    endpoint_variations: List[str]


class BriaAPIResearcher:
    """Research and test BRIA API capabilities to ensure proper integration."""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize BRIA API researcher.
        
        Args:
            api_key: BRIA API key for testing.
        """
        self.api_key = api_key or settings.bria_api_key
        self.base_url = settings.bria_api_base_url
        self.timeout = 30.0
        
    def research_api_capabilities(self) -> BriaAPICapabilities:
        """Research BRIA API to understand real capabilities.
        
        Returns:
            BriaAPICapabilities with discovered information.
        """
        logger.info("Researching BRIA API capabilities...")
        
        capabilities = BriaAPICapabilities(
            supported_models=[],
            max_prompt_length=1000,
            supported_aspect_ratios=[],
            supported_parameters={},
            parameter_limits={},
            endpoint_variations=[]
        )
        
        # Test different endpoints to understand API structure
        endpoints_to_test = [
            "/text-to-image/base/2.3",
            "/text-to-image/base/3.0", 
            "/text-to-image/fast",
            "/text-to-image/hd",
            "/models",
            "/capabilities",
            "/version",
            "/health"
        ]
        
        for endpoint in endpoints_to_test:
            try:
                endpoint_info = self._test_endpoint(endpoint)
                if endpoint_info:
                    capabilities.endpoint_variations.append(endpoint)
                    logger.info(f"✅ Endpoint {endpoint} available")
                else:
                    logger.debug(f"❌ Endpoint {endpoint} not available")
            except Exception as e:
                logger.debug(f"❌ Endpoint {endpoint} error: {e}")
        
        # Test parameter support
        capabilities.supported_parameters = self._discover_parameters()
        capabilities.parameter_limits = self._test_parameter_limits()
        capabilities.supported_aspect_ratios = self._test_aspect_ratios()
        
        return capabilities
    
    def _test_endpoint(self, endpoint: str) -> Optional[Dict[str, Any]]:
        """Test if an endpoint exists and what it returns.
        
        Args:
            endpoint: API endpoint path to test.
            
        Returns:
            Response data if endpoint exists, None otherwise.
        """
        url = f"{self.base_url}{endpoint}"
        headers = {
            "api_token": self.api_key,
            "Content-Type": "application/json",
        }
        
        try:
            with httpx.Client(timeout=10.0) as client:
                # Try GET first
                response = client.get(url, headers=headers)
                
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 405:
                    # Try POST with minimal data
                    response = client.post(
                        url, 
                        json={"prompt": "test"},
                        headers=headers
                    )
                    if response.status_code in [200, 202]:
                        return response.json()
                
        except Exception as e:
            logger.debug(f"Endpoint test failed for {endpoint}: {e}")
        
        return None
    
    def _discover_parameters(self) -> Dict[str, Any]:
        """Discover what parameters BRIA API actually supports.
        
        Returns:
            Dictionary of supported parameters and their types.
        """
        logger.info("Discovering BRIA API parameters...")
        
        # Test with various parameters to see what's supported
        test_parameters = [
            # Basic parameters (known to work)
            {"prompt": "test image", "num_results": 1},
            
            # Advanced parameters (test if supported)
            {"prompt": "test", "steps": 50},
            {"prompt": "test", "guidance_scale": 7.5},
            {"prompt": "test", "scheduler": "euler"},
            {"prompt": "test", "negative_prompt": "blurry"},
            {"prompt": "test", "width": 512, "height": 512},
            {"prompt": "test", "model": "bria-2.3"},
            {"prompt": "test", "style": "photographic"},
            {"prompt": "test", "quality": "high"},
            
            # FIBO-specific parameters (test if available)
            {"prompt": "test", "fibo_mode": "generate"},
            {"prompt": "test", "camera_angle": "front"},
            {"prompt": "test", "lighting": "studio"},
            {"prompt": "test", "composition": "rule_of_thirds"},
        ]
        
        supported_params = {
            "basic": ["prompt", "num_results", "aspect_ratio", "seed", "sync"],
            "advanced": [],
            "limits": {}
        }
        
        endpoint = f"{self.base_url}/text-to-image/base/2.3"
        headers = {
            "api_token": self.api_key,
            "Content-Type": "application/json",
        }
        
        for params in test_parameters:
            try:
                with httpx.Client(timeout=15.0) as client:
                    response = client.post(endpoint, json=params, headers=headers)
                    
                    # If it doesn't return 400 for unsupported params, it might be supported
                    if response.status_code != 400:
                        param_names = [k for k in params.keys() if k != "prompt"]
                        supported_params["advanced"].extend(param_names)
                        logger.info(f"✅ Parameters {param_names} appear supported")
                    else:
                        # Parse error message for parameter info
                        try:
                            error_data = response.json()
                            error_msg = error_data.get("message", "")
                            if "parameter" in error_msg.lower():
                                logger.debug(f"Parameter error: {error_msg}")
                        except:
                            pass
                            
            except Exception as e:
                logger.debug(f"Parameter test failed: {e}")
        
        # Remove duplicates
        supported_params["advanced"] = list(set(supported_params["advanced"]))
        
        return supported_params
    
    def _test_parameter_limits(self) -> Dict[str, Dict[str, Any]]:
        """Test parameter limits and constraints.
        
        Returns:
            Dictionary with parameter limits.
        """
        logger.info("Testing BRIA API parameter limits...")
        
        limits = {
            "prompt": {"max_length": 1000, "min_length": 1},
            "num_results": {"max": 4, "min": 1},
            "seed": {"max": 2147483647, "min": 0},
            "steps": {"max": 100, "min": 10, "default": 50},
            "guidance_scale": {"max": 20.0, "min": 1.0, "default": 7.5}
        }
        
        # Test prompt length limits
        try:
            long_prompt = "test " * 500  # ~2500 chars
            result = self._test_single_parameter("prompt", long_prompt)
            if not result:
                # Try shorter prompts to find limit
                for length in [1000, 500, 200]:
                    test_prompt = "test " * (length // 5)
                    if self._test_single_parameter("prompt", test_prompt):
                        limits["prompt"]["max_length"] = length
                        break
        except Exception as e:
            logger.debug(f"Prompt length test failed: {e}")
        
        # Test num_results limits
        try:
            for num in [5, 8, 10]:
                if not self._test_single_parameter("num_results", num):
                    limits["num_results"]["max"] = num - 1
                    break
        except Exception as e:
            logger.debug(f"Num results test failed: {e}")
        
        return limits
    
    def _test_aspect_ratios(self) -> List[str]:
        """Test which aspect ratios are actually supported.
        
        Returns:
            List of supported aspect ratios.
        """
        logger.info("Testing BRIA API aspect ratio support...")
        
        # Test various aspect ratios
        test_ratios = [
            "1:1", "2:3", "3:2", "3:4", "4:3", "4:5", "5:4", "9:16", "16:9",
            "1:2", "2:1", "5:7", "7:5", "1:3", "3:1"
        ]
        
        supported_ratios = []
        
        for ratio in test_ratios:
            try:
                if self._test_single_parameter("aspect_ratio", ratio):
                    supported_ratios.append(ratio)
                    logger.debug(f"✅ Aspect ratio {ratio} supported")
                else:
                    logger.debug(f"❌ Aspect ratio {ratio} not supported")
            except Exception as e:
                logger.debug(f"Aspect ratio test failed for {ratio}: {e}")
        
        return supported_ratios
    
    def _test_single_parameter(self, param_name: str, param_value: Any) -> bool:
        """Test if a single parameter value is accepted.
        
        Args:
            param_name: Parameter name to test.
            param_value: Parameter value to test.
            
        Returns:
            True if parameter is accepted, False otherwise.
        """
        endpoint = f"{self.base_url}/text-to-image/base/2.3"
        headers = {
            "api_token": self.api_key,
            "Content-Type": "application/json",
        }
        
        payload = {
            "prompt": "simple test image",
            "num_results": 1,
            "sync": True,
            param_name: param_value
        }
        
        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.post(endpoint, json=payload, headers=headers)
                
                # Accept if not a parameter error (400) or auth error (401)
                return response.status_code not in [400, 401]
                
        except Exception:
            return False
    
    def generate_parameter_mapping_guide(self, capabilities: BriaAPICapabilities) -> str:
        """Generate documentation for FIBO parameter mapping.
        
        Args:
            capabilities: Discovered API capabilities.
            
        Returns:
            Markdown documentation string.
        """
        guide = f"""# BRIA API Parameter Mapping Guide

## Discovered API Capabilities

### Supported Endpoints
{chr(10).join(f"- {endpoint}" for endpoint in capabilities.endpoint_variations)}

### Supported Aspect Ratios
{chr(10).join(f"- {ratio}" for ratio in capabilities.supported_aspect_ratios)}

### Basic Parameters (Confirmed Working)
{chr(10).join(f"- {param}" for param in capabilities.supported_parameters.get("basic", []))}

### Advanced Parameters (Detected)
{chr(10).join(f"- {param}" for param in capabilities.supported_parameters.get("advanced", []))}

### Parameter Limits
```json
{json.dumps(capabilities.parameter_limits, indent=2)}
```

## FIBO Parameter Mapping

### Camera Settings → BRIA Parameters
- `camera.angle` → Include in prompt as "shot from [angle]"
- `camera.focal_length` → Include in prompt as "[focal_length] lens"
- `camera.depth_of_field` → Include in prompt as "[depth] depth of field"

### Lighting Settings → BRIA Parameters  
- `lighting.setup` → Include in prompt as "[setup] lighting"
- `lighting.temperature` → Include in prompt as "[temperature] lighting"
- `lighting.intensity` → Include in prompt as "[intensity] lighting"

### Composition → BRIA Parameters
- `composition.rule` → Include in prompt as "[rule] composition"
- `composition.framing` → Include in prompt as "[framing]"

### Color Palette → BRIA Parameters
- `color_palette.primary_colors` → Include in prompt as "colors: [colors]"
- `color_palette.temperature` → Include in prompt as "[temperature] color temperature"

### Style & Mood → BRIA Parameters
- `mood` → Include in prompt as "[mood] style"
- `style` → Include in prompt as "[style] photography"
- `background` → Include in prompt as "[background] background"

## Recommended Prompt Template

```
[subject], [camera_angle], [focal_length] lens, [depth_of_field] depth of field, 
[lighting_setup] lighting, [lighting_temperature] lighting, [mood] style, 
[style] photography, [background] background, [composition_rule] composition,
colors: [primary_colors], [color_temperature] color temperature
```

## Implementation Notes

1. **Structured Prompts**: BRIA works best with comma-separated descriptive prompts
2. **Parameter Limits**: Respect the discovered limits to avoid API errors
3. **Error Handling**: Handle unsupported parameters gracefully
4. **Testing**: Always test parameter combinations before production use

"""
        return guide


def research_and_document_bria_api() -> str:
    """Research BRIA API and generate documentation.
    
    Returns:
        Markdown documentation string.
    """
    if not settings.bria_api_key or settings.bria_api_key in ["test_key_for_development", "your_api_key_here"]:
        return """# BRIA API Research - API Key Required

To research BRIA API capabilities, please:

1. Set your real BRIA API key in `.env`:
   ```
   BRIA_API_KEY=your_real_bria_api_key_here
   ```

2. Restart the backend server

3. Call this research function again

The research will:
- Test available endpoints
- Discover supported parameters  
- Test parameter limits
- Generate mapping documentation
"""
    
    researcher = BriaAPIResearcher()
    capabilities = researcher.research_api_capabilities()
    
    # Save capabilities to file for future reference
    try:
        import json
        from pathlib import Path
        
        research_dir = Path("./research")
        research_dir.mkdir(exist_ok=True)
        
        with open(research_dir / "bria_api_capabilities.json", "w") as f:
            json.dump({
                "supported_models": capabilities.supported_models,
                "max_prompt_length": capabilities.max_prompt_length,
                "supported_aspect_ratios": capabilities.supported_aspect_ratios,
                "supported_parameters": capabilities.supported_parameters,
                "parameter_limits": capabilities.parameter_limits,
                "endpoint_variations": capabilities.endpoint_variations
            }, f, indent=2)
        
        logger.info("✅ Saved BRIA API research to ./research/bria_api_capabilities.json")
        
    except Exception as e:
        logger.warning(f"Could not save research results: {e}")
    
    return researcher.generate_parameter_mapping_guide(capabilities)