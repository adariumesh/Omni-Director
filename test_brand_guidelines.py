#!/usr/bin/env python3
"""Test brand guidelines enforcement system."""

import sys
sys.path.append('/Users/adariprasad/weapon/Omni - Director/backend')

from app.services.brand_guidelines_loader import BrandGuidelinesLoader
from app.services.brand_guard import BrandGuard, BrandGuidelines, BrandViolation
import json

def test_guidelines_loading():
    """Test loading brand guidelines from JSON."""
    print("🧪 Testing Brand Guidelines Loading...")
    
    loader = BrandGuidelinesLoader()
    
    # Load the latest guidelines
    guidelines = loader.load_guidelines()
    
    if guidelines:
        print(f"✅ Loaded: {guidelines.brand_name} v{guidelines.version}")
        print(f"📊 Colors: {len(guidelines.colors)} defined")
        print(f"✍️ Typography: {len(guidelines.typography)} styles")
        print(f"🎨 Style: {guidelines.style.image_style}")
        print(f"🚫 Prohibited: {guidelines.style.prohibited_elements}")
        
        # Test color palette extraction
        palette = loader.get_color_palette(guidelines)
        print(f"🎨 Color Palette: {palette}")
        
        # Test generation parameters
        gen_params = loader.create_generation_params(guidelines)
        print(f"⚙️ Style Modifier: {gen_params['style_modifier']}")
        print(f"❌ Negative Prompt: {gen_params['negative_prompt']}")
        
        return guidelines
    else:
        print("❌ Failed to load guidelines")
        return None

def test_brand_compliance():
    """Test brand compliance checking."""
    print("\n🧪 Testing Brand Compliance Checking...")
    
    loader = BrandGuidelinesLoader()
    guidelines_spec = loader.load_guidelines()
    
    if not guidelines_spec:
        print("❌ No guidelines available for testing")
        return
    
    # Convert to BrandGuard format
    brand_guidelines = BrandGuidelines(
        prohibited_colors=[],  # Will add based on validation
        required_colors=loader.get_primary_colors(guidelines_spec),
        prohibited_words=["competitor", "unauthorized"],
        watermark_enabled=True,
        brand_name=guidelines_spec.brand_name
    )
    
    guard = BrandGuard(brand_guidelines)
    
    # Test prompt compliance
    test_prompts = [
        "A professional corporate image with blue tones",
        "An image with competitor branding and unauthorized content",
        "A clean, minimal design with enterprise styling"
    ]
    
    for prompt in test_prompts:
        result = guard.check_prompt_compliance(prompt)
        print(f"📝 '{prompt[:30]}...'")
        print(f"   ✅ Compliant: {result.compliant}, Score: {result.score:.2f}")
        if result.violations:
            for violation in result.violations:
                print(f"   ⚠️ {violation.severity}: {violation.message}")
    
    # Test JSON compliance
    test_json = {
        "prompt": "Corporate professional image",
        "color_palette": {
            "primary_colors": ["#003366", "#10B981"]  # From guidelines
        },
        "style": "corporate professional"
    }
    
    json_result = guard.check_json_compliance(test_json)
    print(f"\n📄 JSON Compliance: {json_result.compliant}, Score: {json_result.score:.2f}")
    
    return guard

def test_guidelines_enforcement():
    """Test full guidelines enforcement pipeline."""
    print("\n🧪 Testing Guidelines Enforcement Pipeline...")
    
    loader = BrandGuidelinesLoader()
    guidelines = loader.load_guidelines()
    
    if not guidelines:
        return
    
    # Create a sample generation request
    generation_request = {
        "prompt": "A modern office space with professional design",
        "mode": "fibo",
        "aspect_ratio": "16:9"
    }
    
    # Apply brand guidelines to request
    gen_params = loader.create_generation_params(guidelines)
    
    # Enhance the prompt with brand requirements
    enhanced_prompt = (
        f"{generation_request['prompt']}, {gen_params['style_modifier']}"
    )
    
    # Add negative prompt
    enhanced_request = {
        **generation_request,
        "prompt": enhanced_prompt,
        "negative_prompt": gen_params['negative_prompt'],
        "brand_compliant": True,
        "brand_guidelines": {
            "name": guidelines.brand_name,
            "version": guidelines.version,
            "applied_style": guidelines.style.image_style
        }
    }
    
    print(f"📝 Original Prompt: {generation_request['prompt']}")
    print(f"✨ Enhanced Prompt: {enhanced_prompt}")
    print(f"❌ Negative Prompt: {gen_params['negative_prompt']}")
    print(f"🎯 Aspect Ratios: {gen_params['aspect_ratios']}")
    
    return enhanced_request

def test_color_validation():
    """Test color compliance validation."""
    print("\n🧪 Testing Color Validation...")
    
    loader = BrandGuidelinesLoader()
    guidelines = loader.load_guidelines()
    
    if not guidelines:
        return
    
    # Test various colors
    test_colors = [
        "#003366",  # Enterprise Blue (should pass)
        "#10B981",  # Success Green (should pass) 
        "#FF0000",  # Red (should fail)
        "#FFFFFF",  # White (should pass)
        "#123456"   # Random color (should fail)
    ]
    
    validation_results = loader.validate_colors(guidelines, test_colors)
    
    print("🎨 Color Validation Results:")
    for color, is_valid in validation_results.items():
        status = "✅" if is_valid else "❌"
        print(f"   {status} {color}: {'Compliant' if is_valid else 'Non-compliant'}")
    
    return validation_results

if __name__ == "__main__":
    guidelines = test_guidelines_loading()
    guard = test_brand_compliance()
    enhanced_request = test_guidelines_enforcement()
    color_results = test_color_validation()
    
    print(f"\n📋 Brand Guidelines System Test Summary:")
    print(f"Guidelines Loading: {'✅' if guidelines else '❌'}")
    print(f"Compliance Checking: {'✅' if guard else '❌'}")
    print(f"Request Enhancement: {'✅' if enhanced_request else '❌'}")
    print(f"Color Validation: {'✅' if color_results else '❌'}")