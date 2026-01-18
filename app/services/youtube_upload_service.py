"""
YouTube Upload Service
Provides streamlined YouTube video upload with metadata management and thumbnail support.
Integrates patterns from youtube-automate for autonomous_business_platform.
"""

import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import logging
import random

from youtube_helper import (
    get_youtube_service,
    upload_to_youtube,
    YOUTUBE_CATEGORIES
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class YouTubeUploadService:
    """Service for uploading videos to YouTube with automated metadata"""
    
    # Viral title templates for different product types
    VIRAL_TITLE_TEMPLATES = [
        "{product} - You Won't Believe What Happens!",
        "This {product} Changed Everything",
        "{product}: The Secret They Don't Want You to Know",
        "I Tried {product} For 30 Days - Here's What Happened",
        "{product} - Game Changer!",
        "Why Everyone is Talking About {product}",
        "{product} Review: Worth the Hype?",
        "The Truth About {product}",
        "{product} - Must See This!",
        "{product}: Before You Buy, Watch This"
    ]
    
    # High-performing hashtags by category
    TRENDING_HASHTAGS = {
        "product": ["#ProductReview", "#MustHave", "#TrendingNow", "#Viral", "#GameChanger"],
        "tech": ["#Tech", "#Innovation", "#TechReview", "#Gadgets", "#FutureTech"],
        "lifestyle": ["#Lifestyle", "#DailyLife", "#LifeHacks", "#Trending", "#MustWatch"],
        "fitness": ["#Fitness", "#Health", "#Wellness", "#FitLife", "#HealthyLiving"],
        "beauty": ["#Beauty", "#Skincare", "#MakeupReview", "#BeautyTips", "#Glow"],
        "food": ["#Foodie", "#FoodReview", "#TastyFood", "#FoodLovers", "#Delicious"],
        "fashion": ["#Fashion", "#Style", "#OOTD", "#FashionTrends", "#Stylish"],
        "home": ["#HomeDecor", "#InteriorDesign", "#HomeImprovement", "#Organize", "#HomeTips"]
    }
    
    def __init__(self, client_secrets_file: Optional[str] = None, token_file: Optional[str] = None):
        """
        Initialize YouTube upload service
        
        Args:
            client_secrets_file: Path to client_secret.json (default: ./client_secret.json)
            token_file: Path to token.pickle (default: ./token.pickle)
        """
        self.client_secrets_file = client_secrets_file or Path(__file__).parent / 'client_secret.json'
        self.token_file = token_file or Path(__file__).parent / 'token.pickle'
        self.youtube_service = None
        self.is_authenticated = False
    
    def authenticate(self) -> bool:
        """
        Authenticate with YouTube API
        
        Returns:
            True if authentication successful, False otherwise
        """
        try:
            # Check if credentials files exist
            if not Path(self.client_secrets_file).exists():
                logger.error(f"❌ client_secret.json not found at: {self.client_secrets_file}")
                logger.info("💡 Download from Google Cloud Console: https://console.cloud.google.com/apis/credentials")
                self.is_authenticated = False
                return False
            
            # Try to get YouTube service
            self.youtube_service = get_youtube_service(
                client_secrets_file=str(self.client_secrets_file),
                token_file=str(self.token_file)
            )
            
            if not self.youtube_service:
                logger.error("❌ YouTube service initialization failed")
                self.is_authenticated = False
                return False
            
            self.is_authenticated = True
            logger.info("✅ YouTube authentication successful")
            return True
        except FileNotFoundError as e:
            logger.error(f"❌ Credentials file not found: {e}")
            logger.info("💡 Run: python setup_youtube.py")
            self.is_authenticated = False
            return False
        except Exception as e:
            logger.error(f"❌ YouTube authentication failed: {e}")
            logger.info("💡 Try running: python setup_youtube.py")
            self.is_authenticated = False
            return False
    
    def check_credentials(self) -> Dict[str, any]:
        """
        Check YouTube credentials status
        
        Returns:
            Dict with status, message, and credentials info
        """
        result = {
            'authenticated': False,
            'client_secrets_exists': False,
            'token_exists': False,
            'message': ''
        }
        
        # Check for environment variables first
        client_id = os.getenv('YOUTUBE_CLIENT_ID')
        client_secret = os.getenv('YOUTUBE_CLIENT_SECRET')
        
        if client_id and client_secret:
            result['client_secrets_exists'] = True
            logger.info("✅ YouTube credentials found in environment variables")
        elif Path(self.client_secrets_file).exists():
            result['client_secrets_exists'] = True
            logger.info("✅ YouTube client_secret.json found")
        else:
            result['message'] = 'YouTube credentials missing. Add YOUTUBE_CLIENT_ID and YOUTUBE_CLIENT_SECRET to .env or run setup_youtube.py'
            logger.warning("⚠️ No YouTube credentials found")
            return result
        
        # Check for saved token
        if Path(self.token_file).exists():
            result['token_exists'] = True
        
        # Try authentication
        try:
            if self.authenticate():
                result['authenticated'] = True
                result['message'] = 'YouTube API authenticated and ready'
                logger.info("✅ YouTube authentication successful")
            else:
                result['message'] = 'Authentication required - run: python setup_youtube.py'
                logger.warning("⚠️ YouTube authentication needed")
        except Exception as e:
            result['message'] = f'Authentication error: {str(e)}'
            logger.error(f"❌ YouTube auth error: {e}")
        
        return result
    
    def generate_viral_metadata(
        self,
        product_name: str,
        key_benefits: Optional[str] = None,
        target_audience: Optional[str] = None,
        ad_tone: Optional[str] = None,
        product_category: Optional[str] = None,
        use_viral_title: bool = True
    ) -> Dict[str, any]:
        """
        Generate optimized YouTube metadata for maximum virality and exposure using AI
        
        Args:
            product_name: Product/brand name
            key_benefits: Key product benefits/features
            target_audience: Target demographic
            ad_tone: Commercial tone/style
            product_category: Product category for hashtag selection
            use_viral_title: Use viral title templates
        
        Returns:
            Dict with optimized title, description, tags, category
        """
        # Initialize variables
        title = None
        ai_description = None
        
        # Use AI to generate viral YouTube title and description
        try:
            import replicate
            replicate_token = os.getenv('REPLICATE_API_TOKEN')
            if replicate_token:
                logger.info("🤖 Using AI to generate YouTube metadata...")
                
                ai_prompt = f"""Generate a viral YouTube video title and description for this product commercial:

Product: {product_name}
Benefits: {key_benefits or 'Amazing product'}
Target Audience: {target_audience or 'Everyone'}
Tone: {ad_tone or 'Professional'}

Generate:
1. TITLE (max 100 chars, attention-grabbing, SEO-optimized)
2. DESCRIPTION (200-300 words, keyword-rich, includes call-to-action)

Format:
TITLE: [your title here]
DESCRIPTION: [your description here]"""

                output = replicate.run(
                    "meta/meta-llama-3-70b-instruct",
                    input={"prompt": ai_prompt, "max_tokens": 500, "temperature": 0.8}
                )
                ai_text = "".join(output)
                
                # Parse AI output
                title_match = re.search(r'TITLE:\s*(.+?)(?:\n|$)', ai_text, re.IGNORECASE)
                desc_match = re.search(r'DESCRIPTION:\s*(.+)', ai_text, re.IGNORECASE | re.DOTALL)
                
                if title_match:
                    title = title_match.group(1).strip()
                    # Clean up markdown artifacts and formatting
                    title = title.replace('**', '').replace('__', '').replace('*', '').strip()
                    # Remove quotes if AI wrapped title in them
                    if title.startswith('"') and title.endswith('"'):
                        title = title[1:-1].strip()
                    if title.startswith("'") and title.endswith("'"):
                        title = title[1:-1].strip()
                    if len(title) > 100:
                        title = title[:97] + "..."
                    logger.info(f"✅ AI-generated title: {title}")
                
                ai_description = desc_match.group(1).strip() if desc_match else None
        except Exception as e:
            logger.warning(f"⚠️ AI metadata generation failed, using templates: {e}")
        
        # Fallback to template if AI didn't generate title
        if not title:
            if use_viral_title and len(self.VIRAL_TITLE_TEMPLATES) > 0:
                template = random.choice(self.VIRAL_TITLE_TEMPLATES)
                title = template.format(product=product_name)
            else:
                title = f"{product_name} - Must See Commercial"
            
            # Ensure title fits
            if len(title) > 100:
                title = title[:97] + "..."
        
        # Use AI-generated description if available, otherwise build template description
        if ai_description:
            description = ai_description
            logger.info(f"✅ Using AI-generated description ({len(description)} chars)")
        else:
            # Generate optimized description for virality
            description_parts = [
                f"🔥 {product_name} - {ad_tone or 'Must See'}!",
                "",
            ]
            
            # Hook - First 150 chars are critical for search
            if key_benefits:
                benefits_list = [b.strip().lstrip('•-').strip() for b in key_benefits.split('\n') if b.strip()]
                if benefits_list:
                    description_parts.append(f"✨ {benefits_list[0]}")
                    description_parts.append("")
            
            # Key benefits section
            description_parts.append("🎯 What You Get:")
            if key_benefits:
                benefits_list = [b.strip().lstrip('•-').strip() for b in key_benefits.split('\n') if b.strip()]
                for benefit in benefits_list[:5]:
                    description_parts.append(f"✓ {benefit}")
            else:
                description_parts.append(f"✓ Revolutionary {product_name}")
                description_parts.append("✓ Proven results")
                description_parts.append("✓ Perfect for your needs")
            
            description_parts.append("")
            
            # Target audience
            if target_audience:
                description_parts.append(f"👥 Perfect For: {target_audience}")
                description_parts.append("")
            
            # Call to action
            description_parts.extend([
                "💬 What do you think? Comment below!",
                "👍 Like if you found this helpful",
                "🔔 Subscribe for more product reviews",
                "",
                "---",
                f"📦 Product: {product_name}",
                "🤖 AI-Generated Commercial",
                "🎬 Professional Video Production",
                "",
                "🔗 Links & Resources:",
                "• More info in description",
                "• Questions? Ask in comments",
                "",
                "#ProductReview #Viral #Trending"
            ])
            
            description = "\n".join(description_parts)
        
        # Ensure description fits (max 5000 chars)
        if len(description) > 5000:
            description = description[:4997] + "..."
        
        # Generate optimized tags for search + virality
        tags = [
            product_name.replace(" ", "")[:20],  # No spaces, limit length
            "ProductReview",
            "MustSee",
            "Viral",
            "Trending"
        ]
        
        # Add category-specific trending hashtags
        category_key = product_category or "product"
        if category_key.lower() in self.TRENDING_HASHTAGS:
            tags.extend([tag.replace("#", "") for tag in self.TRENDING_HASHTAGS[category_key.lower()][:3]])
        
        # Add tone-specific tags for better targeting
        if ad_tone:
            tone_tags = {
                "Exciting & Energetic": ["Energetic", "Dynamic", "ActionPacked"],
                "Warm & Friendly": ["Friendly", "Welcoming", "Cozy"],
                "Professional & Trustworthy": ["Professional", "Business", "Trustworthy"],
                "Playful & Fun": ["Fun", "Entertainment", "Playful"],
                "Luxury & Premium": ["Luxury", "Premium", "Exclusive"],
                "Urgent & Action-Driven": ["Urgent", "Limited", "ActNow"]
            }
            tags.extend(tone_tags.get(ad_tone, ["Quality", "BestBuy"])[:2])
        
        # Add audience-specific tags
        if target_audience:
            # Extract key words from audience
            audience_words = target_audience.replace("-", " ").replace("(", "").replace(")", "").split()
            for word in audience_words[:2]:
                if len(word) > 3:
                    tags.append(word.capitalize())
        
        # Add general high-performing tags
        tags.extend(["Review", "Worth It", "GameChanger", "MustHave"])
        
        # Remove duplicates and limit to 500 chars total
        tags = list(dict.fromkeys(tags))  # Remove dupes preserving order
        tags_str = ",".join(tags)
        if len(tags_str) > 500:
            # Trim tags to fit
            while len(",".join(tags)) > 500 and len(tags) > 5:
                tags.pop()
        
        # Determine category based on content
        category = '24'  # Entertainment by default
        if ad_tone in ["Professional & Trustworthy"]:
            category = '22'  # People & Blogs
        elif "luxury" in product_name.lower() or "premium" in product_name.lower():
            category = '26'  # Howto & Style
        
        return {
            'title': title,
            'description': description,
            'tags': tags,
            'category': category,
            'privacy': 'unlisted',  # Safe default
            'notify_subscribers': False
        }
    
    def upload_commercial(
        self,
        video_path: str,
        product_name: str,
        metadata: Optional[Dict] = None,
        thumbnail_path: Optional[str] = None,
        **kwargs
    ) -> Optional[Dict]:
        """
        Upload commercial video to YouTube
        
        Args:
            video_path: Path to video file
            product_name: Product name for metadata
            metadata: Optional pre-generated metadata dict
            thumbnail_path: Optional thumbnail image path
            **kwargs: Additional args for generate_metadata_from_campaign
        
        Returns:
            Dict with upload result (id, url, title) or None if failed
        """
        if not self.is_authenticated:
            if not self.authenticate():
                logger.error("❌ Cannot upload - authentication failed")
                return None
        
        # Generate metadata if not provided
        if not metadata:
            metadata = self.generate_viral_metadata(
                product_name=product_name,
                **kwargs
            )
        
        logger.info(f"📤 Uploading video: {Path(video_path).name}")
        logger.info(f"   Title: {metadata['title']}")
        logger.info(f"   Privacy: {metadata.get('privacy', 'unlisted')}")
        
        try:
            result = upload_to_youtube(
                youtube_service=self.youtube_service,
                video_path=video_path,
                metadata=metadata,
                thumbnail_path=thumbnail_path
            )
            
            logger.info(f"✅ Upload successful: {result['url']}")
            return result
            
        except Exception as e:
            logger.error(f"❌ Upload failed: {e}")
            return None
    
    def create_thumbnail_from_video(
        self,
        video_path: str,
        output_path: Optional[str] = None,
        timestamp: float = 1.0
    ) -> Optional[str]:
        """
        Extract a frame from video to use as thumbnail
        
        Args:
            video_path: Path to video file
            output_path: Where to save thumbnail (default: same dir as video)
            timestamp: Timestamp in seconds to extract frame
        
        Returns:
            Path to generated thumbnail or None if failed
        """
        try:
            from moviepy.editor import VideoFileClip
            from PIL import Image
            
            if not output_path:
                video_dir = Path(video_path).parent
                video_name = Path(video_path).stem
                output_path = video_dir / f"{video_name}_thumbnail.jpg"
            
            # Extract frame
            clip = VideoFileClip(video_path)
            frame = clip.get_frame(timestamp)
            clip.close()
            
            # Convert to PIL Image and resize to YouTube recommended size
            img = Image.fromarray(frame)
            img = img.resize((1280, 720), Image.Resampling.LANCZOS)
            
            # Save as high-quality JPEG
            img.save(output_path, 'JPEG', quality=95)
            
            logger.info(f"✅ Thumbnail created: {output_path}")
            return str(output_path)
            
        except Exception as e:
            logger.error(f"❌ Thumbnail creation failed: {e}")
            return None
    
    def get_upload_history(self, limit: int = 10) -> List[Dict]:
        """
        Get recent video uploads from authenticated channel
        
        Args:
            limit: Maximum number of videos to retrieve
        
        Returns:
            List of video dicts with id, title, url, publishedAt
        """
        if not self.is_authenticated:
            if not self.authenticate():
                return []
        
        try:
            # Get uploads playlist ID
            channels_response = self.youtube_service.channels().list(
                mine=True,
                part='contentDetails'
            ).execute()
            
            if not channels_response.get('items'):
                logger.warning("⚠️ No YouTube channel found for this account")
                return []
            
            uploads_playlist_id = channels_response['items'][0]['contentDetails']['relatedPlaylists']['uploads']
            
            # Get recent uploads
            playlist_response = self.youtube_service.playlistItems().list(
                playlistId=uploads_playlist_id,
                part='snippet',
                maxResults=limit
            ).execute()
            
            videos = []
            for item in playlist_response.get('items', []):
                snippet = item['snippet']
                video_id = snippet['resourceId']['videoId']
                videos.append({
                    'id': video_id,
                    'title': snippet['title'],
                    'url': f'https://youtube.com/watch?v={video_id}',
                    'publishedAt': snippet['publishedAt'],
                    'thumbnail': snippet['thumbnails'].get('default', {}).get('url', '')
                })
            
            return videos
            
        except Exception as e:
            error_str = str(e)
            if 'insufficientPermissions' in error_str:
                logger.warning("⚠️ YouTube token needs additional scopes for channel access. Upload functionality still works.")
                logger.info("💡 To fix: Delete token.pickle and re-run to get updated permissions")
            else:
                logger.error(f"❌ Failed to get upload history: {e}")
            return []


# Convenience function for quick uploads
def quick_upload(
    video_path: str,
    title: str,
    description: str = "",
    tags: List[str] = None,
    privacy: str = "unlisted",
    create_thumbnail: bool = True
) -> Optional[str]:
    """
    Quick upload with minimal setup
    
    Returns:
        YouTube video URL or None if failed
    """
    service = YouTubeUploadService()
    
    if not service.authenticate():
        print("❌ Authentication failed")
        return None
    
    metadata = {
        'title': title,
        'description': description or f"Video upload: {title}",
        'tags': tags or [],
        'category': '22',
        'privacy': privacy,
        'notify_subscribers': False
    }
    
    thumbnail_path = None
    if create_thumbnail:
        thumbnail_path = service.create_thumbnail_from_video(video_path)
    
    result = service.upload_commercial(
        video_path=video_path,
        product_name=title,
        metadata=metadata,
        thumbnail_path=thumbnail_path
    )
    
    return result['url'] if result else None


if __name__ == "__main__":
    print("""
YouTube Upload Service
=====================

Setup Instructions:
1. Go to https://console.cloud.google.com/apis/credentials
2. Create OAuth 2.0 Client ID (Desktop application)
3. Download as 'client_secret.json' and place in this directory
4. First run will open browser for authorization
5. Token saved to 'token.pickle' for future use

Example usage:
    from youtube_upload_service import YouTubeUploadService
    
    uploader = YouTubeUploadService()
    
    # Check credentials
    status = uploader.check_credentials()
    print(status)
    
    # Upload video
    result = uploader.upload_commercial(
        video_path="commercial.mp4",
        product_name="EcoFlow Water Bottle",
        key_benefits="Keeps drinks cold 24hrs\\nLeak-proof design\\nRecycled materials",
        target_audience="Fitness Enthusiasts",
        ad_tone="Exciting & Energetic"
    )
    
    if result:
        print(f"Uploaded: {result['url']}")
""")
