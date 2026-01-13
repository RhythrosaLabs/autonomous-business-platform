"""
AI Prompt Template Library
Professional prompt templates for consistent, high-quality AI generation
"""

from typing import Dict, List, Optional
import json
from pathlib import Path


class PromptTemplateLibrary:
    """Centralized library of optimized prompt templates for all AI models."""
    
    def __init__(self):
        self.templates = {
            "video": self._video_templates(),
            "image": self._image_templates(),
            "music": self._music_templates(),
            "voice": self._voice_templates()
        }
    
    def _video_templates(self) -> Dict:
        """Video generation prompt templates."""
        return {
            "product_showcase": {
                "name": "Product Showcase",
                "template": """Professional product showcase video featuring {product_name}.

Camera Movement: Smooth {camera_movement} revealing product details and lifestyle context.

Scene: {scene_description}

Lighting: Professional studio lighting with {lighting_style}. Natural light creates warm, inviting atmosphere.

Style: {visual_style} aesthetic, broadcast quality, commercial production values.

Product Placement: Hero product positioned {product_position}, prominently featured throughout.

Atmosphere: {mood} and {energy_level}, designed for {target_audience}.

Technical: Sharp focus, {resolution} quality, smooth motion, professional color grading.""",
                "variables": ["product_name", "camera_movement", "scene_description", "lighting_style", 
                            "visual_style", "product_position", "mood", "energy_level", "target_audience", "resolution"]
            },
            
            "lifestyle_commercial": {
                "name": "Lifestyle Commercial",
                "template": """Lifestyle commercial showcasing {product_name} in authentic daily life.

Narrative: {narrative_hook} - shows real people experiencing the benefits of {product_name}.

Setting: {setting} with natural, lived-in atmosphere. Contemporary {design_style} interior design.

Camera Work: {camera_style} cinematography. Movements include {camera_movements}.

Mood: {mood} with {emotional_tone} emotional resonance. Music and visuals create {feeling}.

Product Integration: Organic product placement showing {use_case}. Benefits naturally demonstrated.

Cast: {talent_description} engaging with product authentically.

Color Grade: {color_palette} palette with {color_treatment} post-processing.

Pacing: {pacing} editing rhythm matching {music_tempo} background score.""",
                "variables": ["product_name", "narrative_hook", "setting", "design_style", "camera_style",
                            "camera_movements", "mood", "emotional_tone", "feeling", "use_case",
                            "talent_description", "color_palette", "color_treatment", "pacing", "music_tempo"]
            },
            
            "quick_promo": {
                "name": "Quick Promo (Social Media)",
                "template": """High-energy {platform} promo for {product_name}.

Hook: Immediate visual impact with {hook_style}. Grabs attention in first second.

Message: {key_message} delivered through dynamic visuals and {text_style} on-screen text.

Visuals: Fast-paced {cut_style} cuts, {transition_style} transitions. {visual_effects} effects.

Product: {product_name} featured prominently with {highlight_technique}.

Call-to-Action: Clear {cta_type} ending with {cta_text}.

Aspect Ratio: {aspect_ratio} optimized for {platform}.

Duration: {duration} seconds - perfect for {platform} algorithm.

Vibe: {vibe} energy matching {trend_style} trends.""",
                "variables": ["platform", "product_name", "hook_style", "key_message", "text_style",
                            "cut_style", "transition_style", "visual_effects", "highlight_technique",
                            "cta_type", "cta_text", "aspect_ratio", "duration", "vibe", "trend_style"]
            },
            
            "cinematic_story": {
                "name": "Cinematic Story",
                "template": """Cinematic storytelling piece for {product_name}.

Story Arc: {story_structure} narrative following {protagonist} as they {journey}.

Visual Language: {cinematography_style} cinematography with {shot_types}. 
{lighting_approach} lighting creates {visual_mood}.

Sound Design: {sound_style} audio landscape. {music_description} score underscores emotional beats.

Product Role: {product_name} serves as {story_function} in the narrative.

Themes: Explores themes of {themes}, resonating with {target_demo} audience values.

Pacing: {act_structure} structure with {pacing_style} rhythm. 
Building from {opening_tone} to {climax_tone} to {resolution_tone}.

Cinematography: {lens_style} lenses, {depth_style} depth of field, {movement_style} camera movement.

Grade: {color_grade_style} color grading with {contrast_level} contrast and {saturation_level} saturation.""",
                "variables": ["product_name", "story_structure", "protagonist", "journey", "cinematography_style",
                            "shot_types", "lighting_approach", "visual_mood", "sound_style", "music_description",
                            "story_function", "themes", "target_demo", "act_structure", "pacing_style",
                            "opening_tone", "climax_tone", "resolution_tone", "lens_style", "depth_style",
                            "movement_style", "color_grade_style", "contrast_level", "saturation_level"]
            }
        }
    
    def _image_templates(self) -> Dict:
        """Image generation prompt templates."""
        return {
            "product_hero": {
                "name": "Product Hero Shot",
                "template": """{product_name} professional hero shot.

Composition: {composition_style} with product as focal point. {background_description} background.

Lighting: {lighting_setup} creating {lighting_mood}. {shadow_description} shadows add depth.

Product Details: Sharp focus on {detail_focus}. {material_description} materials clearly visible.

Color: {color_scheme} color palette. {color_harmony} harmony throughout composition.

Style: {photography_style} photography, {quality_level} quality, {post_processing} post-processing.

Props: {props_description} supporting elements enhance without distracting.

Angle: {camera_angle} angle showing {product_features}.

Format: {resolution} resolution, {aspect_ratio} aspect ratio, {format} format.""",
                "variables": ["product_name", "composition_style", "background_description", "lighting_setup",
                            "lighting_mood", "shadow_description", "detail_focus", "material_description",
                            "color_scheme", "color_harmony", "photography_style", "quality_level",
                            "post_processing", "props_description", "camera_angle", "product_features",
                            "resolution", "aspect_ratio", "format"]
            },
            
            "lifestyle_scene": {
                "name": "Lifestyle Scene",
                "template": """{product_name} in authentic lifestyle setting.

Environment: {location_type} showcasing real-world use. {decor_style} decor with {aesthetic} aesthetic.

Context: {usage_context} demonstrating {benefit} benefit naturally.

Lighting: {light_source} lighting creates {atmosphere}. {time_of_day} ambiance.

Composition: {composition_rule} composition. Product placed {product_placement}.

People: {people_description} interacting with product naturally. {expression} expressions show {emotion}.

Details: {environmental_details} add authenticity and relatability.

Mood: {overall_mood} capturing {target_feeling} feeling.

Style: {photo_style} style, {quality_descriptor} quality, {realism_level} realism.""",
                "variables": ["product_name", "location_type", "decor_style", "aesthetic", "usage_context",
                            "benefit", "light_source", "atmosphere", "time_of_day", "composition_rule",
                            "product_placement", "people_description", "expression", "emotion",
                            "environmental_details", "overall_mood", "target_feeling", "photo_style",
                            "quality_descriptor", "realism_level"]
            }
        }
    
    def _music_templates(self) -> Dict:
        """Music generation prompt templates."""
        return {
            "commercial_background": {
                "name": "Commercial Background Music",
                "template": """{genre} background music for commercial.

Mood: {mood} with {energy_level} energy. {emotional_tone} emotional quality.

Tempo: {bpm} BPM, {rhythm_style} rhythm pattern.

Instrumentation: {instruments} creating {sonic_texture} texture.

Structure: {structure} with {progression} progression.

Mix: {mix_style} mix with {balance} balance. {frequency_focus} frequencies emphasized.

Purpose: Supports {message_type} message without overwhelming narration/dialogue.""",
                "variables": ["genre", "mood", "energy_level", "emotional_tone", "bpm", "rhythm_style",
                            "instruments", "sonic_texture", "structure", "progression", "mix_style",
                            "balance", "frequency_focus", "message_type"]
            }
        }
    
    def _voice_templates(self) -> Dict:
        """Voice/narration prompt templates."""
        return {
            "commercial_voiceover": {
                "name": "Commercial Voiceover",
                "template": """{voice_type} voice delivering {message_type} message.

Tone: {tone} with {personality} personality. {emotion} emotional quality.

Pacing: {pacing} delivery at {speed} speed. {emphasis_style} emphasis on key points.

Audience: Speaking to {target_audience} with {formality_level} formality.

Purpose: {purpose} while maintaining {brand_voice} brand voice.""",
                "variables": ["voice_type", "message_type", "tone", "personality", "emotion",
                            "pacing", "speed", "emphasis_style", "target_audience", "formality_level",
                            "purpose", "brand_voice"]
            }
        }
    
    def get_template(self, category: str, template_name: str) -> Optional[Dict]:
        """Get a specific template."""
        return self.templates.get(category, {}).get(template_name)
    
    def fill_template(self, category: str, template_name: str, variables: Dict) -> str:
        """Fill a template with provided variables."""
        template_data = self.get_template(category, template_name)
        if not template_data:
            return ""
        
        template = template_data["template"]
        
        # Fill in provided variables
        for key, value in variables.items():
            placeholder = "{" + key + "}"
            template = template.replace(placeholder, str(value))
        
        # Remove unfilled placeholders
        import re
        template = re.sub(r'\{[^}]+\}', '[AUTO]', template)
        
        return template
    
    def list_templates(self, category: Optional[str] = None) -> Dict:
        """List available templates."""
        if category:
            return {name: data["name"] for name, data in self.templates.get(category, {}).items()}
        else:
            result = {}
            for cat, templates in self.templates.items():
                result[cat] = {name: data["name"] for name, data in templates.items()}
            return result
    
    def save_custom_template(self, category: str, name: str, template: str, variables: List[str]):
        """Save a custom template to the library."""
        if category not in self.templates:
            self.templates[category] = {}
        
        self.templates[category][name] = {
            "name": name,
            "template": template,
            "variables": variables,
            "custom": True
        }
    
    def export_templates(self, filepath: str):
        """Export templates to JSON file."""
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, 'w') as f:
            json.dump(self.templates, f, indent=2)
    
    def import_templates(self, filepath: str):
        """Import templates from JSON file."""
        with open(filepath, 'r') as f:
            imported = json.load(f)
            for category, templates in imported.items():
                if category not in self.templates:
                    self.templates[category] = {}
                self.templates[category].update(templates)


# Smart prompt enhancement system
class PromptEnhancer:
    """Enhance prompts with quality modifiers and best practices."""
    
    @staticmethod
    def add_quality_modifiers(prompt: str, quality_level: str = "high") -> str:
        """Add quality modifiers to prompt."""
        quality_terms = {
            "low": "decent quality, acceptable detail",
            "medium": "good quality, clear detail, professional",
            "high": "high quality, exceptional detail, professional production, broadcast quality",
            "ultra": "ultra high quality, perfect detail, cinematic masterpiece, award-winning production"
        }
        
        modifier = quality_terms.get(quality_level, quality_terms["high"])
        return f"{prompt}\n\nQuality: {modifier}, sharp focus, perfect exposure, professional color grading."
    
    @staticmethod
    def add_technical_specs(prompt: str, resolution: str = "1080p", fps: int = 30) -> str:
        """Add technical specifications."""
        tech_spec = f"\n\nTechnical: {resolution} resolution, {fps}fps, smooth motion, no artifacts, clean render."
        return prompt + tech_spec
    
    @staticmethod
    def add_negative_prompts(prompt: str, avoid_list: Optional[List[str]] = None) -> str:
        """Add negative prompt guidance."""
        if avoid_list is None:
            avoid_list = ["blurry", "low quality", "distorted", "watermark", "text", "artifacts"]
        
        negative = f"\n\nAvoid: {', '.join(avoid_list)}"
        return prompt + negative
    
    @staticmethod
    def optimize_for_model(prompt: str, model: str) -> str:
        """Optimize prompt for specific AI model."""
        optimizations = {
            "sora": "\n\nOptimized for Sora: cinematic camera movement, realistic physics, coherent motion.",
            "kling": "\n\nOptimized for Kling: dynamic animation, smooth transitions, creative effects.",
            "flux": "\n\nOptimized for Flux: photorealistic detail, accurate colors, sharp textures.",
            "stable-diffusion": "\n\nOptimized for SD: clear composition, balanced lighting, coherent style."
        }
        
        return prompt + optimizations.get(model.lower(), "")


if __name__ == "__main__":
    # Demo the library
    print("🎨 Prompt Template Library Demo\n")
    
    library = PromptTemplateLibrary()
    
    print("Available Templates:")
    for category, templates in library.list_templates().items():
        print(f"\n{category.upper()}:")
        for key, name in templates.items():
            print(f"  - {key}: {name}")
    
    print("\n" + "="*60)
    print("Example: Product Showcase Video")
    print("="*60 + "\n")
    
    variables = {
        "product_name": "EcoWave Water Bottle",
        "camera_movement": "dolly-in from medium to close-up",
        "scene_description": "Modern minimalist kitchen with natural wood accents",
        "lighting_style": "soft diffused natural light from large windows",
        "visual_style": "Clean contemporary",
        "product_position": "center frame on marble countertop",
        "mood": "Calm and refreshing",
        "energy_level": "moderate",
        "target_audience": "health-conscious millennials",
        "resolution": "4K"
    }
    
    prompt = library.fill_template("video", "product_showcase", variables)
    print(prompt)
    
    print("\n" + "="*60)
    print("Enhanced with Quality Modifiers:")
    print("="*60 + "\n")
    
    enhancer = PromptEnhancer()
    enhanced = enhancer.add_quality_modifiers(prompt, "ultra")
    enhanced = enhancer.add_technical_specs(enhanced, "4K", 60)
    enhanced = enhancer.optimize_for_model(enhanced, "sora")
    print(enhanced)
