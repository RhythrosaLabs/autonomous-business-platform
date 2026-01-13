from dataclasses import dataclass, asdict, field
from typing import Optional, List, Dict
from datetime import datetime

@dataclass
class APIConfig:
    """API configuration with validation"""
    printify_token: str
    replicate_token: str
    flux_model: str = "black-forest-labs/flux-dev"
    use_local_models: bool = False
    local_models_path: str = ""
    
    def is_valid(self) -> bool:
        if self.use_local_models:
            return bool(self.printify_token.strip() and self.local_models_path)
        return bool(self.printify_token.strip() and self.replicate_token.strip())

@dataclass
class ProductTemplate:
    """Product template configuration"""
    name: str
    product_type: str
    base_price: float
    prompt_template: str
    tags: List[str]
    collection_name: str = ""
    auto_publish: bool = False
    generate_marketing: bool = True
    
    def apply_prompt(self, custom_text: str) -> str:
        """Apply custom text to template"""
        return self.prompt_template.replace("{prompt}", custom_text)

@dataclass
class PriceRule:
    """Dynamic pricing rule"""
    product_type: str
    base_price: float
    markup_percent: float = 50.0

@dataclass
class ProductDetails:
    """Product creation details"""
    prompt: str
    product_type: str
    price: float = 25.0
    tags: List[str] = field(default_factory=list)
    collection: str = ""
    shop_id: str = ""
    campaign_audience: str = ""
    ad_tone: str = ""
    call_to_action: str = ""
    video_style: str = ""
    blog_tone: str = ""
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []
    
    def get_enhanced_prompt(self) -> str:
        """Generate enhanced prompt with better composition and transparent background"""
        return (f"{self.prompt}, centered composition, product photography, "
                f"professional studio lighting, transparent background, high detail, "
                f"8k quality, commercial photography --ar 1:1 --style raw")
    
    def get_seo_title(self) -> str:
        """Generate SEO-optimized title"""
        keywords = self.prompt.split()[:5]
        return f"{' '.join(keywords).title()} - Premium {self.product_type.title()}"
    
    def get_seo_description(self) -> str:
        """Generate SEO-optimized description"""
        return (f"Discover our unique {self.product_type} featuring {self.prompt}. "
                f"High-quality print, fast shipping, and satisfaction guaranteed. "
                f"Perfect gift for art lovers and design enthusiasts. "
                f"Shop now for exclusive designs!")

@dataclass
class WorkflowResult:
    """Result from product creation workflow"""
    status: str
    message: str
    product_id: Optional[str] = None
    assets_path: Optional[str] = None
    item_index: int = 0
    image_url: Optional[str] = None
    created_at: str = ""
    shop_id: str = ""
    # New fields for asset aggregation and campaign docs
    assets: Optional[Dict[str, list]] = None
    title: str = ""
    description: str = ""
    tags: List[str] = field(default_factory=list)
    image_filename: str = ""
    mockup_filename: str = ""
    campaign_audience: str = ""
    campaign_cta: str = ""
    ad_tone: str = ""
    video_style: str = ""
    blog_tone: str = ""


@dataclass
class CampaignProductPlan:
    """AI-generated configuration for a single product within a campaign."""
    product_type: str
    prompt: str
    price: float
    tags: List[str] = field(default_factory=list)
    audience: str = ""
    ad_tone: str = ""
    call_to_action: str = ""
    video_style: str = ""
    blog_tone: str = ""


@dataclass
class CampaignPlan:
    """High-level AI-generated campaign blueprint."""
    campaign_name: str
    concept: str
    target_audience: str
    summary: str
    primary_call_to_action: str
    blog_tone: str
    product_lineup: List[CampaignProductPlan] = field(default_factory=list)

@dataclass
class ScheduledJob:
    """Scheduled product creation job"""
    id: int
    scheduled_time: datetime
    prompts: List[str]
    product_type: str
    price: float
    shop_id: str
    status: str = "pending"  # pending, running, completed, failed
