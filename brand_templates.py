"""
Brand Template Library
======================
Pre-built brand templates with colors, fonts, styles, and presets.
"""

import streamlit as st
import json
from typing import Dict, List, Optional, Any
from pathlib import Path
from datetime import datetime
import uuid
import logging

logger = logging.getLogger(__name__)

# Pre-built brand templates
PRESET_TEMPLATES = {
    "minimalist_modern": {
        "id": "minimalist_modern",
        "name": "Minimalist Modern",
        "description": "Clean, modern aesthetic with lots of white space",
        "category": "Professional",
        "colors": {
            "primary": "#000000",
            "secondary": "#666666",
            "accent": "#FF6B6B",
            "background": "#FFFFFF",
            "text": "#1A1A1A"
        },
        "fonts": {
            "heading": "Inter",
            "body": "Inter",
            "accent": "Space Mono"
        },
        "style": {
            "tone": "professional, clean, minimal",
            "imagery": "high contrast, geometric, abstract",
            "layout": "centered, spacious, grid-based"
        },
        "prompts": {
            "product": "minimalist product photography, white background, soft shadows, clean aesthetic",
            "lifestyle": "minimal lifestyle, clean spaces, neutral tones, modern interior",
            "marketing": "bold typography, minimal design, strong contrast, geometric shapes"
        }
    },
    "bold_vibrant": {
        "id": "bold_vibrant",
        "name": "Bold & Vibrant",
        "description": "Eye-catching colors and dynamic designs",
        "category": "Creative",
        "colors": {
            "primary": "#FF3366",
            "secondary": "#6C5CE7",
            "accent": "#00D9FF",
            "background": "#0D0D0D",
            "text": "#FFFFFF"
        },
        "fonts": {
            "heading": "Bebas Neue",
            "body": "Open Sans",
            "accent": "Permanent Marker"
        },
        "style": {
            "tone": "energetic, bold, youthful",
            "imagery": "vibrant colors, dynamic angles, motion blur",
            "layout": "asymmetric, overlapping, bold"
        },
        "prompts": {
            "product": "dynamic product shot, neon lighting, cyberpunk aesthetic, vibrant colors",
            "lifestyle": "energetic lifestyle, urban setting, night scenes, neon lights",
            "marketing": "bold graphics, gradient overlays, 3D elements, maximalist design"
        }
    },
    "organic_natural": {
        "id": "organic_natural",
        "name": "Organic & Natural",
        "description": "Earth tones and natural textures",
        "category": "Eco-Friendly",
        "colors": {
            "primary": "#4A6741",
            "secondary": "#8B7355",
            "accent": "#C9A86C",
            "background": "#F5F1EB",
            "text": "#2C2C2C"
        },
        "fonts": {
            "heading": "Playfair Display",
            "body": "Lora",
            "accent": "Caveat"
        },
        "style": {
            "tone": "natural, organic, sustainable",
            "imagery": "earth tones, natural textures, botanical elements",
            "layout": "flowing, organic shapes, balanced"
        },
        "prompts": {
            "product": "natural lighting, organic textures, botanical backdrop, earthy tones",
            "lifestyle": "outdoor setting, natural environment, sustainable living, green aesthetic",
            "marketing": "hand-drawn elements, natural paper textures, botanical illustrations"
        }
    },
    "luxury_premium": {
        "id": "luxury_premium",
        "name": "Luxury Premium",
        "description": "Sophisticated and high-end aesthetic",
        "category": "Premium",
        "colors": {
            "primary": "#C9A227",
            "secondary": "#1A1A2E",
            "accent": "#D4AF37",
            "background": "#0F0F0F",
            "text": "#F0F0F0"
        },
        "fonts": {
            "heading": "Cormorant Garamond",
            "body": "Montserrat",
            "accent": "Great Vibes"
        },
        "style": {
            "tone": "elegant, luxurious, exclusive",
            "imagery": "dramatic lighting, gold accents, rich textures",
            "layout": "symmetric, centered, refined"
        },
        "prompts": {
            "product": "dramatic studio lighting, black background, gold accents, premium feel",
            "lifestyle": "luxury lifestyle, high-end interior, sophisticated setting",
            "marketing": "elegant typography, gold foil effect, marble textures, premium design"
        }
    },
    "retro_vintage": {
        "id": "retro_vintage",
        "name": "Retro Vintage",
        "description": "Nostalgic vibes with vintage aesthetics",
        "category": "Retro",
        "colors": {
            "primary": "#E07A5F",
            "secondary": "#3D405B",
            "accent": "#F2CC8F",
            "background": "#F4F1DE",
            "text": "#2D2D2D"
        },
        "fonts": {
            "heading": "Righteous",
            "body": "Roboto Slab",
            "accent": "Pacifico"
        },
        "style": {
            "tone": "nostalgic, warm, playful",
            "imagery": "vintage filters, film grain, retro patterns",
            "layout": "classic, bordered, badge-style"
        },
        "prompts": {
            "product": "vintage photography style, warm tones, film grain, retro aesthetic",
            "lifestyle": "70s inspired, warm lighting, retro interior, nostalgic mood",
            "marketing": "vintage poster style, retro typography, distressed textures, badge design"
        }
    },
    "tech_futuristic": {
        "id": "tech_futuristic",
        "name": "Tech Futuristic",
        "description": "Cutting-edge technology aesthetic",
        "category": "Tech",
        "colors": {
            "primary": "#00F0FF",
            "secondary": "#8B5CF6",
            "accent": "#10B981",
            "background": "#0A0A0B",
            "text": "#E5E5E5"
        },
        "fonts": {
            "heading": "Orbitron",
            "body": "Exo 2",
            "accent": "Share Tech Mono"
        },
        "style": {
            "tone": "futuristic, innovative, cutting-edge",
            "imagery": "holographic, glitch effects, digital patterns",
            "layout": "modular, grid-based, angular"
        },
        "prompts": {
            "product": "futuristic setting, holographic effects, tech environment, sci-fi aesthetic",
            "lifestyle": "smart home, technology integration, futuristic living space",
            "marketing": "glitch effects, circuit patterns, holographic gradients, tech UI elements"
        }
    },
    "playful_fun": {
        "id": "playful_fun",
        "name": "Playful & Fun",
        "description": "Bright, cheerful, and kid-friendly",
        "category": "Family",
        "colors": {
            "primary": "#FF6B9D",
            "secondary": "#4ECDC4",
            "accent": "#FFE66D",
            "background": "#FFFFFF",
            "text": "#2D3436"
        },
        "fonts": {
            "heading": "Fredoka One",
            "body": "Nunito",
            "accent": "Shadows Into Light"
        },
        "style": {
            "tone": "playful, cheerful, friendly",
            "imagery": "bright colors, cartoon elements, doodles",
            "layout": "rounded, bubbly, sticker-style"
        },
        "prompts": {
            "product": "bright colorful background, playful setting, fun props, cheerful mood",
            "lifestyle": "family moments, outdoor fun, colorful activities, happy vibes",
            "marketing": "cartoon illustrations, doodles, sticker style, bright gradients"
        }
    },
    "streetwear_urban": {
        "id": "streetwear_urban",
        "name": "Streetwear Urban",
        "description": "Urban street culture aesthetic",
        "category": "Fashion",
        "colors": {
            "primary": "#FF4500",
            "secondary": "#1C1C1C",
            "accent": "#FFFF00",
            "background": "#121212",
            "text": "#FFFFFF"
        },
        "fonts": {
            "heading": "Anton",
            "body": "Oswald",
            "accent": "Bangers"
        },
        "style": {
            "tone": "urban, edgy, street culture",
            "imagery": "graffiti, urban backdrop, street photography",
            "layout": "bold, stacked, distressed"
        },
        "prompts": {
            "product": "urban backdrop, street style, graffiti walls, city environment",
            "lifestyle": "street fashion, skateboarding, urban culture, city life",
            "marketing": "graffiti style, spray paint effects, distressed textures, bold type"
        }
    }
}

# Industry-specific templates
INDUSTRY_TEMPLATES = {
    "fitness": {
        "id": "fitness",
        "name": "Fitness & Sports",
        "colors": {"primary": "#E63946", "secondary": "#1D3557", "accent": "#F77F00"},
        "prompts": {
            "product": "gym setting, athletic aesthetic, dynamic lighting, motivational",
            "lifestyle": "workout scene, athletic lifestyle, fitness motivation",
            "marketing": "bold typography, action shots, motivational quotes"
        }
    },
    "beauty": {
        "id": "beauty",
        "name": "Beauty & Cosmetics",
        "colors": {"primary": "#E8B4B8", "secondary": "#2D2D2D", "accent": "#D4AF37"},
        "prompts": {
            "product": "beauty flat lay, soft lighting, marble background, elegant",
            "lifestyle": "beauty routine, self-care, glamorous lifestyle",
            "marketing": "soft gradients, elegant typography, luxury feel"
        }
    },
    "food": {
        "id": "food",
        "name": "Food & Beverage",
        "colors": {"primary": "#D62828", "secondary": "#003049", "accent": "#FCBF49"},
        "prompts": {
            "product": "food photography, appetizing, warm lighting, fresh ingredients",
            "lifestyle": "dining experience, cooking scene, food culture",
            "marketing": "appetizing imagery, rustic textures, hand-lettering"
        }
    },
    "travel": {
        "id": "travel",
        "name": "Travel & Adventure",
        "colors": {"primary": "#219EBC", "secondary": "#023047", "accent": "#FFB703"},
        "prompts": {
            "product": "travel gear, adventure setting, outdoor backdrop",
            "lifestyle": "travel destinations, adventure activities, wanderlust",
            "marketing": "scenic photography, passport stamps, map elements"
        }
    },
    "pets": {
        "id": "pets",
        "name": "Pets & Animals",
        "colors": {"primary": "#588157", "secondary": "#3A5A40", "accent": "#DAD7CD"},
        "prompts": {
            "product": "pet products, cute animals, natural setting",
            "lifestyle": "pet lifestyle, outdoor adventures with pets, cozy moments",
            "marketing": "paw prints, playful graphics, heartwarming imagery"
        }
    }
}


class BrandTemplate:
    """Represents a complete brand template."""
    
    def __init__(self, data: Dict):
        self.id = data.get('id', str(uuid.uuid4()))
        self.name = data.get('name', 'Untitled')
        self.description = data.get('description', '')
        self.category = data.get('category', 'Custom')
        self.colors = data.get('colors', {})
        self.fonts = data.get('fonts', {})
        self.style = data.get('style', {})
        self.prompts = data.get('prompts', {})
        self.logo_url = data.get('logo_url')
        self.created_at = data.get('created_at', datetime.now().isoformat())
        self.modified_at = data.get('modified_at', datetime.now().isoformat())
    
    def to_dict(self) -> Dict:
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'category': self.category,
            'colors': self.colors,
            'fonts': self.fonts,
            'style': self.style,
            'prompts': self.prompts,
            'logo_url': self.logo_url,
            'created_at': self.created_at,
            'modified_at': self.modified_at
        }
    
    def get_prompt_modifier(self, prompt_type: str = 'product') -> str:
        """Get prompt modifier for AI generation."""
        base = self.prompts.get(prompt_type, '')
        style = self.style.get('tone', '')
        colors = ', '.join(self.colors.values())[:50]
        
        modifiers = [m for m in [base, style] if m]
        return ', '.join(modifiers) if modifiers else ''
    
    def enhance_prompt(self, base_prompt: str, prompt_type: str = 'product') -> str:
        """Enhance a prompt with brand style."""
        modifier = self.get_prompt_modifier(prompt_type)
        if modifier:
            return f"{base_prompt}, {modifier}"
        return base_prompt


class TemplateLibrary:
    """Manage brand templates."""
    
    def __init__(self, storage_dir: Optional[Path] = None):
        self.storage_dir = storage_dir or Path.home() / ".pod_wizard" / "templates"
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.templates: Dict[str, BrandTemplate] = {}
        self._load_templates()
    
    def _load_templates(self):
        """Load all templates including presets and custom."""
        # Load presets
        for template_id, data in PRESET_TEMPLATES.items():
            self.templates[template_id] = BrandTemplate(data)
        
        for template_id, data in INDUSTRY_TEMPLATES.items():
            full_data = {**PRESET_TEMPLATES.get('minimalist_modern', {}), **data}
            self.templates[template_id] = BrandTemplate(full_data)
        
        # Load custom templates
        for file in self.storage_dir.glob("*.json"):
            try:
                with open(file, 'r') as f:
                    data = json.load(f)
                    self.templates[data['id']] = BrandTemplate(data)
            except Exception as e:
                logger.warning(f"Failed to load template {file}: {e}")
    
    def get_template(self, template_id: str) -> Optional[BrandTemplate]:
        return self.templates.get(template_id)
    
    def list_templates(self, category: Optional[str] = None) -> List[BrandTemplate]:
        templates = list(self.templates.values())
        if category:
            templates = [t for t in templates if t.category == category]
        return sorted(templates, key=lambda t: t.name)
    
    def get_categories(self) -> List[str]:
        return sorted(set(t.category for t in self.templates.values()))
    
    def save_template(self, template: BrandTemplate):
        """Save a custom template."""
        template.modified_at = datetime.now().isoformat()
        self.templates[template.id] = template
        
        file_path = self.storage_dir / f"{template.id}.json"
        with open(file_path, 'w') as f:
            json.dump(template.to_dict(), f, indent=2)
    
    def delete_template(self, template_id: str):
        """Delete a custom template."""
        if template_id in self.templates:
            del self.templates[template_id]
            file_path = self.storage_dir / f"{template_id}.json"
            if file_path.exists():
                file_path.unlink()
    
    def create_template(self, name: str, **kwargs) -> BrandTemplate:
        """Create a new custom template."""
        data = {
            'id': str(uuid.uuid4()),
            'name': name,
            'category': 'Custom',
            **kwargs
        }
        template = BrandTemplate(data)
        self.save_template(template)
        return template


def render_template_library():
    """Render the template library UI."""
    st.markdown("### 🎨 Brand Template Library")
    
    library = TemplateLibrary()
    
    # Category filter
    categories = ["All"] + library.get_categories()
    selected_category = st.selectbox("Filter by Category", categories)
    
    # Template grid
    templates = library.list_templates(
        category=None if selected_category == "All" else selected_category
    )
    
    cols = st.columns(3)
    for idx, template in enumerate(templates):
        with cols[idx % 3]:
            with st.container():
                # Color preview
                color_bar = " ".join([
                    f'<span style="display:inline-block;width:20px;height:20px;background:{c};border-radius:3px;"></span>'
                    for c in list(template.colors.values())[:5]
                ])
                
                # Font info
                fonts = template.fonts or {}
                heading_font = fonts.get('heading_family', fonts.get('heading', 'Default'))
                body_font = fonts.get('body_family', fonts.get('body', 'Default'))
                
                st.markdown(f"""
                <div style="border:1px solid #333;border-radius:8px;padding:12px;margin-bottom:10px;">
                    <h4 style="margin:0 0 8px 0;">{template.name}</h4>
                    <p style="color:#888;font-size:12px;margin:0 0 8px 0;">{template.category}</p>
                    <div style="margin-bottom:8px;">{color_bar}</div>
                    <p style="font-size:11px;color:#999;margin:0 0 4px 0;">🔤 {heading_font} / {body_font}</p>
                    <p style="font-size:11px;color:#666;margin:0;">{template.description[:60]}...</p>
                </div>
                """, unsafe_allow_html=True)
                
                if st.button("Use Template", key=f"use_{template.id}", use_container_width=True):
                    st.session_state['active_brand_template'] = template.id
                    st.success(f"✅ Now using: {template.name}")
    
    # Create custom template
    st.markdown("---")
    with st.expander("➕ Create Custom Template"):
        new_name = st.text_input("Template Name", key="new_template_name")
        new_desc = st.text_area("Description", key="new_template_desc")
        
        st.markdown("**Colors**")
        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            primary = st.color_picker("Primary", "#3498db", key="new_primary")
        with col2:
            secondary = st.color_picker("Secondary", "#2c3e50", key="new_secondary")
        with col3:
            accent = st.color_picker("Accent", "#e74c3c", key="new_accent")
        with col4:
            background = st.color_picker("Background", "#ffffff", key="new_background")
        with col5:
            text_color = st.color_picker("Text", "#333333", key="new_text_color")
        
        st.markdown("**Typography**")
        
        # Font presets for quick selection
        font_presets = {
            "Modern & Clean": {"heading": "Montserrat", "body": "Open Sans"},
            "Elegant Serif": {"heading": "Playfair Display", "body": "Lora"},
            "Bold Impact": {"heading": "Oswald", "body": "Roboto"},
            "Friendly & Rounded": {"heading": "Nunito", "body": "Quicksand"},
            "Minimalist": {"heading": "Inter", "body": "Inter"},
            "Vintage Retro": {"heading": "Abril Fatface", "body": "Merriweather"},
            "Tech & Modern": {"heading": "Space Grotesk", "body": "IBM Plex Sans"},
            "Handwritten Feel": {"heading": "Pacifico", "body": "Caveat"},
            "Custom": {"heading": "", "body": ""}
        }
        
        font_preset_choice = st.selectbox("Font Preset", list(font_presets.keys()), key="font_preset_choice")
        
        font_col1, font_col2 = st.columns(2)
        with font_col1:
            # All available Google Fonts for custom selection
            font_families = [
                "Inter", "Roboto", "Open Sans", "Montserrat", "Lato", "Poppins", "Nunito",
                "Playfair Display", "Merriweather", "Lora", "Libre Baskerville",
                "Oswald", "Bebas Neue", "Anton", "Righteous",
                "Space Grotesk", "IBM Plex Sans", "Source Sans Pro",
                "Quicksand", "Comfortaa", "Varela Round",
                "Pacifico", "Caveat", "Dancing Script", "Great Vibes",
                "Abril Fatface", "Cormorant Garamond"
            ]
            
            default_heading = font_presets[font_preset_choice]["heading"] or "Montserrat"
            heading_idx = font_families.index(default_heading) if default_heading in font_families else 0
            
            heading_font = st.selectbox("Heading Font", font_families, index=heading_idx, key="new_heading_font")
            heading_weight = st.select_slider("Heading Weight", options=["300", "400", "500", "600", "700", "800", "900"], value="700", key="new_heading_weight")
            heading_size = st.select_slider("Heading Size", options=["24px", "28px", "32px", "36px", "40px", "48px"], value="32px", key="new_heading_size")
        
        with font_col2:
            default_body = font_presets[font_preset_choice]["body"] or "Open Sans"
            body_idx = font_families.index(default_body) if default_body in font_families else 0
            
            body_font = st.selectbox("Body Font", font_families, index=body_idx, key="new_body_font")
            body_weight = st.select_slider("Body Weight", options=["300", "400", "500", "600", "700"], value="400", key="new_body_weight")
            body_size = st.select_slider("Body Size", options=["14px", "15px", "16px", "17px", "18px"], value="16px", key="new_body_size")
        
        # Font preview
        st.markdown("**Preview:**")
        st.markdown(f"""
        <div style="background:{background};padding:20px;border-radius:8px;border:1px solid #333;">
            <h2 style="font-family:'{heading_font}',sans-serif;font-weight:{heading_weight};font-size:{heading_size};color:{text_color};margin:0 0 10px 0;">
                Heading Preview
            </h2>
            <p style="font-family:'{body_font}',sans-serif;font-weight:{body_weight};font-size:{body_size};color:{text_color};margin:0;">
                This is how your body text will look. The quick brown fox jumps over the lazy dog.
            </p>
            <button style="background:{primary};color:white;border:none;padding:10px 20px;border-radius:4px;margin-top:15px;font-family:'{body_font}',sans-serif;">
                Call to Action
            </button>
        </div>
        """, unsafe_allow_html=True)
        
        style_tone = st.text_input("Style Tone", placeholder="e.g., modern, professional, playful", key="new_tone")
        
        if st.button("Create Template", type="primary"):
            if new_name:
                template = library.create_template(
                    name=new_name,
                    description=new_desc,
                    colors={
                        "primary": primary, 
                        "secondary": secondary, 
                        "accent": accent,
                        "background": background,
                        "text": text_color
                    },
                    fonts={
                        "heading_family": heading_font,
                        "heading_weight": heading_weight,
                        "heading_size": heading_size,
                        "body_family": body_font,
                        "body_weight": body_weight,
                        "body_size": body_size
                    },
                    style={"tone": style_tone}
                )
                st.success(f"✅ Created template: {template.name}")
                st.rerun()
            else:
                st.warning("Please enter a template name")


def get_active_template() -> Optional[BrandTemplate]:
    """Get the currently active brand template."""
    if 'active_brand_template' in st.session_state:
        library = TemplateLibrary()
        return library.get_template(st.session_state['active_brand_template'])
    return None


def enhance_prompt_with_brand(prompt: str, prompt_type: str = 'product') -> str:
    """Enhance a prompt with the active brand template."""
    template = get_active_template()
    if template:
        return template.enhance_prompt(prompt, prompt_type)
    return prompt
