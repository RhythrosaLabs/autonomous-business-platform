"""
Credential Manager - Centralized credential storage and retrieval for browser automation
Provides secure access to login credentials for browser-use tasks
"""
import os
from typing import Dict, Optional, List
from dotenv import load_dotenv
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

# Load environment variables
env_path = Path(__file__).parent / '.env'
if env_path.exists():
    load_dotenv(env_path)
else:
    load_dotenv()


class CredentialManager:
    """
    Centralized credential management for browser automation tasks.
    Automatically loads credentials from .env and provides formatted context for AI agents.
    """
    
    def __init__(self):
        """Initialize credential manager and load all available credentials"""
        self.credentials = self._load_credentials()
        
    def _load_credentials(self) -> Dict[str, Dict[str, str]]:
        """
        Load all credentials from environment variables.
        
        Returns:
            Dict mapping service names to credential dictionaries
        """
        creds = {}
        
        # Twitter/X credentials
        twitter_username = os.getenv('TWITTER_USERNAME')
        twitter_password = os.getenv('TWITTER_PASSWORD')
        twitter_email = os.getenv('TWITTER_EMAIL')
        if twitter_username and twitter_password:
            creds['twitter'] = {
                'username': twitter_username,
                'password': twitter_password,
                'email': twitter_email or twitter_username,
                'url': 'https://twitter.com',
                'login_url': 'https://twitter.com/login'
            }
            logger.info("✅ Twitter credentials loaded")
        
        # Facebook credentials
        facebook_email = os.getenv('FACEBOOK_EMAIL')
        facebook_password = os.getenv('FACEBOOK_PASSWORD')
        if facebook_email and facebook_password:
            creds['facebook'] = {
                'email': facebook_email,
                'password': facebook_password,
                'username': facebook_email,
                'url': 'https://facebook.com',
                'login_url': 'https://facebook.com/login'
            }
            logger.info("✅ Facebook credentials loaded")
        
        # Instagram credentials
        instagram_username = os.getenv('INSTAGRAM_USERNAME')
        instagram_password = os.getenv('INSTAGRAM_PASSWORD')
        if instagram_username and instagram_password:
            creds['instagram'] = {
                'username': instagram_username,
                'password': instagram_password,
                'url': 'https://instagram.com',
                'login_url': 'https://instagram.com/accounts/login/'
            }
            logger.info("✅ Instagram credentials loaded")
        
        # LinkedIn credentials
        linkedin_email = os.getenv('LINKEDIN_EMAIL')
        linkedin_password = os.getenv('LINKEDIN_PASSWORD')
        if linkedin_email and linkedin_password:
            creds['linkedin'] = {
                'email': linkedin_email,
                'password': linkedin_password,
                'username': linkedin_email,
                'url': 'https://linkedin.com',
                'login_url': 'https://www.linkedin.com/login'
            }
            logger.info("✅ LinkedIn credentials loaded")
        
        # YouTube/Google credentials
        google_email = os.getenv('GOOGLE_EMAIL') or os.getenv('YOUTUBE_EMAIL')
        google_password = os.getenv('GOOGLE_PASSWORD') or os.getenv('YOUTUBE_PASSWORD')
        if google_email and google_password:
            creds['youtube'] = {
                'email': google_email,
                'password': google_password,
                'username': google_email,
                'url': 'https://youtube.com',
                'login_url': 'https://accounts.google.com'
            }
            creds['google'] = creds['youtube']  # Alias
            logger.info("✅ Google/YouTube credentials loaded")
        
        # TikTok credentials
        tiktok_username = os.getenv('TIKTOK_USERNAME')
        tiktok_password = os.getenv('TIKTOK_PASSWORD')
        if tiktok_username and tiktok_password:
            creds['tiktok'] = {
                'username': tiktok_username,
                'password': tiktok_password,
                'url': 'https://tiktok.com',
                'login_url': 'https://www.tiktok.com/login'
            }
            logger.info("✅ TikTok credentials loaded")
        
        # Reddit credentials
        reddit_username = os.getenv('REDDIT_USERNAME')
        reddit_password = os.getenv('REDDIT_PASSWORD')
        if reddit_username and reddit_password:
            creds['reddit'] = {
                'username': reddit_username,
                'password': reddit_password,
                'url': 'https://reddit.com',
                'login_url': 'https://www.reddit.com/login'
            }
            logger.info("✅ Reddit credentials loaded")
        
        # Pinterest credentials
        pinterest_email = os.getenv('PINTEREST_EMAIL')
        pinterest_password = os.getenv('PINTEREST_PASSWORD')
        if pinterest_email and pinterest_password:
            creds['pinterest'] = {
                'email': pinterest_email,
                'password': pinterest_password,
                'username': pinterest_email,
                'url': 'https://pinterest.com',
                'login_url': 'https://www.pinterest.com/login'
            }
            logger.info("✅ Pinterest credentials loaded")
        
        return creds
    
    def get_credentials(self, service: str) -> Optional[Dict[str, str]]:
        """
        Get credentials for a specific service.
        
        Args:
            service: Service name (twitter, facebook, instagram, etc.)
            
        Returns:
            Dictionary with credentials or None if not found
        """
        service_lower = service.lower()
        
        # Handle aliases
        aliases = {
            'x': 'twitter',
            'x.com': 'twitter',
            'fb': 'facebook',
            'ig': 'instagram',
            'insta': 'instagram',
            'yt': 'youtube'
        }
        
        service_key = aliases.get(service_lower, service_lower)
        return self.credentials.get(service_key)
    
    def has_credentials(self, service: str) -> bool:
        """Check if credentials exist for a service"""
        return self.get_credentials(service) is not None
    
    def list_available_services(self) -> List[str]:
        """Get list of services with configured credentials"""
        return list(self.credentials.keys())
    
    def get_login_context(self, service: str) -> str:
        """
        Get formatted login context for AI agent.
        
        Args:
            service: Service name
            
        Returns:
            Formatted string with login instructions and credentials for AI
        """
        creds = self.get_credentials(service)
        if not creds:
            return f"❌ No credentials found for {service}. Please add to .env file."
        
        context = f"""
🔐 CREDENTIALS AVAILABLE FOR {service.upper()}:

Login URL: {creds.get('login_url', creds.get('url'))}
"""
        
        # Add available credential fields
        if 'username' in creds:
            context += f"Username: {creds['username']}\n"
        if 'email' in creds:
            context += f"Email: {creds['email']}\n"
        if 'password' in creds:
            context += f"Password: {creds['password']}\n"
        
        context += """
INSTRUCTIONS:
1. Navigate to the login URL
2. Enter the provided credentials
3. Complete any 2FA/CAPTCHA if prompted (wait for user)
4. Proceed with the requested task after login
"""
        
        return context
    
    def get_full_context(self) -> str:
        """
        Get full credential context for AI agent.
        Shows all available services and login info.
        """
        services = self.list_available_services()
        
        if not services:
            return """
❌ NO CREDENTIALS CONFIGURED

Please add credentials to your .env file:

TWITTER_USERNAME=your_username
TWITTER_PASSWORD=your_password
TWITTER_EMAIL=your_email@example.com

FACEBOOK_EMAIL=your_email@example.com
FACEBOOK_PASSWORD=your_password

INSTAGRAM_USERNAME=your_username
INSTAGRAM_PASSWORD=your_password

LINKEDIN_EMAIL=your_email@example.com
LINKEDIN_PASSWORD=your_password

GOOGLE_EMAIL=your_email@gmail.com
GOOGLE_PASSWORD=your_password

TIKTOK_USERNAME=your_username
TIKTOK_PASSWORD=your_password

REDDIT_USERNAME=your_username
REDDIT_PASSWORD=your_password

PINTEREST_EMAIL=your_email@example.com
PINTEREST_PASSWORD=your_password
"""
        
        context = f"""
🔐 CREDENTIAL MANAGER - AVAILABLE ACCOUNTS

You have access to credentials for the following services:
{', '.join([s.upper() for s in services])}

When a user asks you to:
- "go to twitter" or "post to twitter"
- "visit facebook" or "share on facebook"
- "log in to instagram"
- etc.

YOU SHOULD AUTOMATICALLY:
1. Detect which service they're referring to
2. Use the stored credentials to log in
3. Complete the requested task

EXAMPLE:
User: "Go to twitter and post this message"
You: 
  - Navigate to https://twitter.com/login
  - Use TWITTER_USERNAME and TWITTER_PASSWORD to log in
  - Post the message
  
USER SHOULD NEVER HAVE TO PROVIDE LOGIN INFO AGAIN!

Available credentials:
"""
        
        for service in services:
            creds = self.credentials[service]
            context += f"\n{service.upper()}:"
            context += f"\n  URL: {creds.get('url')}"
            if 'username' in creds:
                context += f"\n  Username: {creds['username']}"
            if 'email' in creds:
                context += f"\n  Email: {creds['email']}"
            context += "\n  (Password available)"
        
        return context


# Global instance
_credential_manager = None


def get_credential_manager() -> CredentialManager:
    """Get or create global credential manager instance"""
    global _credential_manager
    if _credential_manager is None:
        _credential_manager = CredentialManager()
    return _credential_manager
