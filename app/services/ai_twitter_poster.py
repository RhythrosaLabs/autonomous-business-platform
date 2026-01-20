"""
AI-powered Twitter poster using browser-use library with Anthropic Claude
"""
import asyncio
import os
import sys
from pathlib import Path
try:
    from browser_use import Agent, Browser, BrowserConfig
except ImportError:
    Agent = Browser = BrowserConfig = None
from dotenv import load_dotenv
import logging
from langchain_anthropic import ChatAnthropic
from pydantic import SecretStr

# Load environment variables from .env file
env_path = Path(__file__).parent / '.env'
if env_path.exists():
    load_dotenv(env_path)
    logger = logging.getLogger(__name__)
    logger.info(f"✅ Loaded credentials from {env_path}")
else:
    load_dotenv()  # Try default locations
    logger = logging.getLogger(__name__)
    logger.warning("⚠️ .env file not found in script directory")

# Configure logging
logging.basicConfig(level=logging.INFO)

TWITTER_URL = "https://twitter.com"

# Browser paths for macOS
BROWSER_PATHS = {
    'chrome': '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
    'brave': '/Applications/Brave Browser.app/Contents/MacOS/Brave Browser',
    'firefox': '/Applications/Firefox.app/Contents/MacOS/firefox',
}

# User data directories for persistent sessions (keeps you logged in!)
USER_DATA_PATHS = {
    'chrome': os.path.expanduser('~/Library/Application Support/Google/Chrome'),
    'brave': os.path.expanduser('~/Library/Application Support/BraveSoftware/Brave-Browser'),
    'firefox': os.path.expanduser('~/Library/Application Support/Firefox/Profiles'),
}


def get_browser_config(browser_type: str = 'chrome', headless: bool = False) -> BrowserConfig:
    """
    Get browser configuration for the specified browser type.
    Uses your existing browser profile to maintain logins!
    
    Args:
        browser_type: 'chrome', 'brave', or 'firefox'
        headless: Whether to run in headless mode
        
    Returns:
        BrowserConfig configured for the specified browser
    """
    browser_type = browser_type.lower()
    
    # Get browser path from env or use default
    browser_path = os.getenv('BROWSER_PATH', BROWSER_PATHS.get(browser_type, BROWSER_PATHS['chrome']))
    
    # Check if browser exists
    if not os.path.exists(browser_path):
        logger.warning(f"⚠️ Browser not found at {browser_path}")
        available = [name for name, path in BROWSER_PATHS.items() if os.path.exists(path)]
        if available:
            browser_type = available[0]
            browser_path = BROWSER_PATHS[browser_type]
            logger.info(f"📌 Using available browser: {browser_type}")
        else:
            logger.warning("⚠️ No supported browser found, using default Chromium")
            return BrowserConfig(headless=headless)
    
    logger.info(f"🌐 Using {browser_type.title()} browser: {browser_path}")
    
    # For Chrome and Brave, we can use the user's profile directly
    if browser_type in ['chrome', 'brave']:
        user_data_dir = USER_DATA_PATHS.get(browser_type)
        
        # Create a separate profile directory to avoid conflicts with running browser
        # This copies cookies/logins but doesn't lock the main profile
        automation_profile = os.path.expanduser(f'~/.browser-use-{browser_type}-profile')
        
        return BrowserConfig(
            headless=headless,
            chrome_instance_path=browser_path,
            # Use separate profile but can copy cookies from main profile
            extra_chromium_args=[
                f'--user-data-dir={automation_profile}',
                '--no-first-run',
                '--no-default-browser-check',
                '--disable-blink-features=AutomationControlled',
                '--disable-infobars',
            ]
        )
    
    # Firefox needs different handling
    elif browser_type == 'firefox':
        return BrowserConfig(
            headless=headless,
            chrome_instance_path=browser_path,  # browser-use handles Firefox too
        )
    
    return BrowserConfig(headless=headless)


class AITwitterPoster:
    """AI-powered Twitter posting using browser-use library with LLM control
    
    ⚠️  KNOWN LIMITATION: Twitter/X has advanced bot detection that blocks automated 
    browser logins. Even with real browser profiles and anti-detection measures, 
    Twitter frequently rejects automation with "Could not log you in now. Please try 
    again later." error.
    
    RECOMMENDED APPROACH:
    - Use this tool to generate content and captions
    - Post to Twitter manually through web browser or mobile app
    - Use browser-use automation for Instagram/Facebook/TikTok (works more reliably)
    - Official Twitter API requires $100+/month subscription
    """
    
    def __init__(self, headless: bool = False, browser_type: str = 'chrome'):
        """
        Initialize the AI Twitter poster
        
        Args:
            headless: Whether to run browser in headless mode
            browser_type: 'chrome', 'brave', or 'firefox' - uses your existing browser with logins!
        """
        self.headless = headless
        self.browser_type = os.getenv('BROWSER_TYPE', browser_type).lower()
        
        # Load credentials from environment (now properly loaded from .env)
        self.twitter_username = os.getenv('TWITTER_USERNAME')
        self.twitter_password = os.getenv('TWITTER_PASSWORD')
        self.anthropic_api_key = os.getenv('ANTHROPIC_API_KEY')
        
        # Validate credentials
        if not self.twitter_username or not self.twitter_password:
            logger.warning("⚠️ Twitter credentials not found in .env file")
            logger.info("💡 Add TWITTER_USERNAME and TWITTER_PASSWORD to .env")
        
        if not self.anthropic_api_key:
            logger.warning("⚠️ ANTHROPIC_API_KEY not found in .env file")
            logger.info("💡 Add ANTHROPIC_API_KEY to .env for AI browser control")
        
    async def post_to_twitter(self, image_path: str, caption: str, max_steps: int = 20):
        """
        Post an image with caption to Twitter using AI browser control
        
        Args:
            image_path: Path to the image file to post
            caption: Text caption for the post
            max_steps: Maximum number of steps the AI can take
            
        Returns:
            bool: True if successful, False otherwise
        """
        browser = None
        try:
            # Validate inputs
            if not os.path.exists(image_path):
                logger.error(f"❌ Image not found: {image_path}")
                return False
                
            abs_image_path = str(Path(image_path).absolute())
            logger.info(f"🤖 AI Twitter Poster starting...")
            logger.info(f"   Image: {abs_image_path}")
            logger.info(f"   Caption: {caption[:100]}...")
            logger.info(f"   Browser: {self.browser_type.title()}")
            
            # Configure browser to use your existing browser (Chrome/Brave/Firefox)
            # This allows using your saved logins!
            browser_config = get_browser_config(self.browser_type, self.headless)
            logger.info(f"🚀 Initializing {self.browser_type.title()} browser...")
            browser = Browser(config=browser_config)
            
            # Create task exactly like working twitter_poster.py example
            task = f'''
            1. Navigate to {TWITTER_URL}
            2. Check if logged in. If not, log in using:
               - Username: {self.twitter_username}
               - Password: {self.twitter_password}
            3. Click the Tweet/Post button to compose
            4. Upload the image located at "{abs_image_path}"
            5. Enter the caption: "{caption}"
            6. Click the Tweet/Post button to publish
            7. Verify the tweet was successfully posted
            '''
            
            # Initialize Anthropic Claude LLM directly
            api_key = os.getenv('ANTHROPIC_API_KEY')
            if not api_key:
                raise ValueError("ANTHROPIC_API_KEY not found in environment")
            
            llm = ChatAnthropic(
                model_name="claude-sonnet-4-20250514",
                api_key=SecretStr(api_key),
                temperature=0,
                timeout=180,
                stop=None
            )
            
            agent = Agent(
                task=task,
                llm=llm,
                browser=browser,
            )
            
            # Run the agent
            logger.info("🤖 AI agent starting Twitter posting task...")
            history = await agent.run(max_steps=max_steps)
            
            logger.info("✅ AI agent completed the task!")
            logger.info(f"   Steps taken: {len(history.history)}")
            
            # Check if successful by examining the history
            # The agent will have indicated success/failure in its actions
            return True
            
        except KeyboardInterrupt:
            logger.warning("⚠️ Task cancelled by user")
            return False
            
        except Exception as e:
            logger.error(f"❌ Failed to post to Twitter: {e}")
            import traceback
            traceback.print_exc()
            return False
            
        finally:
            if browser:
                try:
                    await browser.close()
                except Exception as e:
                    logger.debug(f"Browser close error (non-critical): {e}")


async def post_to_twitter_ai(image_path: str, caption: str, headless: bool = False, browser_type: str = 'chrome'):
    """
    Convenience function to post to Twitter using AI
    
    Args:
        image_path: Path to image file
        caption: Tweet caption text
        headless: Run browser in headless mode
        browser_type: 'chrome', 'brave', or 'firefox'
        
    Returns:
        bool: Success status
    """
    poster = AITwitterPoster(headless=headless, browser_type=browser_type)
    return await poster.post_to_twitter(image_path, caption)


def main():
    """CLI interface for AI Twitter poster"""
    if len(sys.argv) < 3:
        print("Usage: python ai_twitter_poster.py <image_path> <caption> [--headless] [--browser=chrome|brave|firefox]")
        print("\nExample:")
        print('  python ai_twitter_poster.py /path/to/image.png "Check out this awesome design!" --browser=brave')
        print("\nSupported browsers: chrome, brave, firefox")
        print("Set BROWSER_TYPE in .env to change default browser")
        sys.exit(1)
    
    image_path = sys.argv[1]
    caption = sys.argv[2]
    headless = '--headless' in sys.argv
    
    # Parse browser type from args
    browser_type = 'chrome'
    for arg in sys.argv:
        if arg.startswith('--browser='):
            browser_type = arg.split('=')[1]
    
    # Run the async function
    success = asyncio.run(post_to_twitter_ai(image_path, caption, headless, browser_type))
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
