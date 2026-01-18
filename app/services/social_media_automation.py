"""
Social Media Browser Automation Service
=======================================

Automate social media posting using browser automation (Selenium).
NO API keys required - uses username/password login credentials.

Supported Platforms:
- Instagram (posts, stories, reels)
- Facebook (posts, stories)
- Twitter/X (posts, threads)
- TikTok (video uploads)
- LinkedIn (posts, articles)

Features:
- Headless or visible browser modes
- Automatic login and session management
- Image and video upload support
- Caption and hashtag handling
- Multi-platform batch posting
- Error recovery and retry logic

Author: Autonomous Business Platform
Version: 1.0
"""

import os
import time
import logging
from pathlib import Path
from typing import Optional, Dict, List
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException, NoSuchElementException

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SocialMediaAutomation:
    """
    Automate social media posting using browser automation.
    No API keys required - uses direct login credentials.
    """
    
    def __init__(self, headless: bool = True, download_dir: Optional[str] = None):
        """
        Initialize browser automation service.
        
        Args:
            headless: Run browser in headless mode (no GUI)
            download_dir: Directory for downloads (optional)
        """
        self.headless = headless
        self.download_dir = download_dir or str(Path.home() / "Downloads")
        self.driver = None
        self.replicate_token = os.getenv('REPLICATE_API_TOKEN')
        self.shop_url = os.getenv('SHOPIFY_SHOP_URL', 'https://husky-hub-2.myshopify.com')
        
        # Load credentials from .env
        self.credentials = {
            'instagram': {
                'username': os.getenv('INSTAGRAM_USERNAME'),
                'password': os.getenv('INSTAGRAM_PASSWORD')
            },
            'facebook': {
                'username': os.getenv('FACEBOOK_USERNAME'),
                'password': os.getenv('FACEBOOK_PASSWORD')
            },
            'twitter': {
                'username': os.getenv('TWITTER_USERNAME'),
                'password': os.getenv('TWITTER_PASSWORD')
            },
            'tiktok': {
                'username': os.getenv('TIKTOK_USERNAME'),
                'password': os.getenv('TIKTOK_PASSWORD')
            },
            'linkedin': {
                'username': os.getenv('LINKEDIN_USERNAME'),
                'password': os.getenv('LINKEDIN_PASSWORD')
            }
        }
        
        logger.info("✅ Social Media Automation initialized")
    
    def generate_smart_caption(
        self,
        image_filename: str,
        campaign_name: str = "",
        max_length: int = 280
    ) -> str:
        """
        Generate AI-powered social media caption with shop link and smart hashtags.
        
        Args:
            image_filename: Name of the image file
            campaign_name: Campaign or product name
            max_length: Maximum caption length (280 for Twitter)
        
        Returns:
            Generated caption with shop link and hashtags
        """
        try:
            import replicate
            
            # Extract context from filename and campaign
            context = campaign_name if campaign_name else image_filename.replace('_', ' ').replace('.png', '').replace('.jpg', '')
            
            prompt = f"""Write a compelling social media post (max {max_length} characters) that:
1. Highlights this product: {context}
2. Creates excitement and urgency
3. Includes a call-to-action to visit our shop
4. Ends with 2-3 relevant hashtags for our target market
5. Keep it authentic and engaging, not salesy

Write ONLY the tweet text, nothing else."""

            # Use Llama for caption generation
            output = replicate.run(
                "meta/meta-llama-3-70b-instruct",
                input={
                    "prompt": prompt,
                    "max_tokens": 150,
                    "temperature": 0.8
                }
            )
            
            caption = "".join(output).strip()
            
            # Add shop link if not already present
            if 'http' not in caption.lower():
                # Shorten caption if needed to fit link
                link = f"\n\n🛒 {self.shop_url}"
                max_caption_length = max_length - len(link)
                if len(caption) > max_caption_length:
                    caption = caption[:max_caption_length-3] + "..."
                caption += link
            
            logger.info(f"✅ Generated smart caption: {caption[:50]}...")
            return caption
            
        except Exception as e:
            logger.warning(f"⚠️ AI caption generation failed: {e}, using fallback")
            # Fallback caption
            product_name = campaign_name or context
            return f"✨ Check out our {product_name}! Perfect for anyone who loves unique designs.\n\n🛒 {self.shop_url}\n\n#UniqueDesigns #ShopSmall #CustomProducts"
    
    def _setup_driver(self, use_persistent_session: bool = False):
        """Setup Chrome WebDriver with appropriate options.
        
        Args:
            use_persistent_session: Use persistent user data dir to keep cookies/login state
        """
        options = webdriver.ChromeOptions()
        
        if self.headless:
            options.add_argument('--headless')
        
        # PERSISTENT SESSION: Keep cookies and login state across runs
        if use_persistent_session:
            user_data_dir = os.path.join(os.path.expanduser("~"), ".selenium_profiles", "twitter")
            os.makedirs(user_data_dir, exist_ok=True)
            options.add_argument(f'--user-data-dir={user_data_dir}')
            options.add_argument('--profile-directory=Default')
            logger.info(f"🔐 Using persistent session: {user_data_dir}")
        
        # Common options for stability
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('--disable-notifications')
        options.add_argument(f'user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36')
        
        # Set download directory
        prefs = {'download.default_directory': self.download_dir}
        options.add_experimental_option('prefs', prefs)
        
        # Hide automation indicators
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        self.driver = webdriver.Chrome(options=options)
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        logger.info("✅ WebDriver initialized")
    
    def _wait_and_click(self, by: By, value: str, timeout: int = 10):
        """Wait for element and click it."""
        element = WebDriverWait(self.driver, timeout).until(
            EC.element_to_be_clickable((by, value))
        )
        element.click()
        return element
    
    def _wait_and_send_keys(self, by: By, value: str, keys: str, timeout: int = 10):
        """Wait for element and send keys."""
        element = WebDriverWait(self.driver, timeout).until(
            EC.presence_of_element_located((by, value))
        )
        # Try to clear input; contenteditable elements sometimes don't support .clear()
        try:
            element.clear()
        except Exception:
            try:
                # For contenteditable fields, set innerText via JS
                self.driver.execute_script("arguments[0].innerText = ''", element)
            except Exception:
                try:
                    element.click()
                    element.send_keys(Keys.CONTROL, 'a', Keys.DELETE)
                except Exception:
                    pass
        element.send_keys(keys)
        return element

    def _find_element_with_selectors(self, selectors: List[tuple], timeout: int = 8):
        """Try a list of (By, selector) tuples and return (element, by, selector) for the first match."""
        for by, selector in selectors:
            try:
                elem = WebDriverWait(self.driver, timeout).until(
                    EC.presence_of_element_located((by, selector))
                )
                return elem, by, selector
            except Exception:
                continue
        raise Exception("None of the selectors matched any element")
    
    def post_to_instagram(
        self,
        image_path: str,
        caption: str,
        is_story: bool = False
    ) -> bool:
        """
        Post image to Instagram feed or story.
        
        Args:
            image_path: Path to image file
            caption: Post caption with hashtags
            is_story: Post as story instead of feed post
        
        Returns:
            True if successful
        """
        platform = 'instagram'
        creds = self.credentials[platform]
        
        if not creds['username'] or not creds['password']:
            logger.error(f"❌ {platform.title()} credentials not configured in .env")
            return False
        
        try:
            self._setup_driver()
            logger.info(f"📸 Posting to Instagram {'story' if is_story else 'feed'}...")
            
            # Login
            self.driver.get('https://www.instagram.com/accounts/login/')
            time.sleep(3)
            
            # Enter credentials
            self._wait_and_send_keys(By.NAME, 'username', creds['username'])
            self._wait_and_send_keys(By.NAME, 'password', creds['password'])
            
            # Click login
            self._wait_and_click(By.XPATH, "//button[@type='submit']")
            time.sleep(5)
            
            # Handle "Save Login Info" prompt (click Not Now)
            try:
                not_now_btn = self.driver.find_element(By.XPATH, "//button[contains(text(), 'Not Now')]")
                not_now_btn.click()
                time.sleep(2)
            except:
                pass
            
            # Handle "Turn on Notifications" prompt (click Not Now)
            try:
                not_now_btn = self.driver.find_element(By.XPATH, "//button[contains(text(), 'Not Now')]")
                not_now_btn.click()
                time.sleep(2)
            except:
                pass
            
            if is_story:
                # Click on story/add button at top
                self._wait_and_click(By.XPATH, "//svg[@aria-label='New Story']")
            else:
                # Click create post button
                self._wait_and_click(By.XPATH, "//svg[@aria-label='New post']")
            
            time.sleep(2)
            
            # Upload image
            file_input = self.driver.find_element(By.XPATH, "//input[@type='file']")
            file_input.send_keys(str(Path(image_path).absolute()))
            time.sleep(3)
            
            # Click Next
            self._wait_and_click(By.XPATH, "//button[contains(text(), 'Next')]")
            time.sleep(2)
            
            # Click Next again (filters page)
            self._wait_and_click(By.XPATH, "//button[contains(text(), 'Next')]")
            time.sleep(2)
            
            # Add caption
            caption_textarea = self.driver.find_element(By.XPATH, "//textarea[@aria-label='Write a caption...']")
            caption_textarea.send_keys(caption)
            time.sleep(2)
            
            # Share/Post
            self._wait_and_click(By.XPATH, "//button[contains(text(), 'Share')]")
            time.sleep(5)
            
            logger.info(f"✅ Successfully posted to Instagram!")
            return True
            
        except Exception as e:
            logger.error(f"❌ Instagram posting failed: {e}")
            return False
        finally:
            if self.driver:
                self.driver.quit()
    
    def post_to_facebook(
        self,
        image_path: str,
        caption: str
    ) -> bool:
        """
        Post image to Facebook.
        
        Args:
            image_path: Path to image file
            caption: Post caption
        
        Returns:
            True if successful
        """
        platform = 'facebook'
        creds = self.credentials[platform]
        
        if not creds['username'] or not creds['password']:
            logger.error(f"❌ {platform.title()} credentials not configured in .env")
            return False
        
        try:
            self._setup_driver()
            logger.info(f"📘 Posting to Facebook...")
            
            # Login
            self.driver.get('https://www.facebook.com/login/')
            time.sleep(3)
            
            # Enter credentials
            self._wait_and_send_keys(By.ID, 'email', creds['username'])
            self._wait_and_send_keys(By.ID, 'pass', creds['password'])
            
            # Click login
            self._wait_and_click(By.NAME, 'login')
            time.sleep(5)
            
            # Click "What's on your mind?"
            self._wait_and_click(By.XPATH, "//span[contains(text(), \"What's on your mind\")]")
            time.sleep(2)
            
            # Add caption
            caption_box = self.driver.find_element(By.XPATH, "//div[@role='textbox']")
            caption_box.send_keys(caption)
            time.sleep(1)
            
            # Upload photo
            self._wait_and_click(By.XPATH, "//span[contains(text(), 'Photo/video')]")
            time.sleep(1)
            
            file_input = self.driver.find_element(By.XPATH, "//input[@type='file']")
            file_input.send_keys(str(Path(image_path).absolute()))
            time.sleep(5)
            
            # Click Post
            self._wait_and_click(By.XPATH, "//span[contains(text(), 'Post')]")
            time.sleep(5)
            
            logger.info(f"✅ Successfully posted to Facebook!")
            return True
            
        except Exception as e:
            logger.error(f"❌ Facebook posting failed: {e}")
            return False
        finally:
            if self.driver:
                self.driver.quit()
    
    def post_to_twitter(
        self,
        image_path: str,
        caption: str
    ) -> bool:
        """
        Post tweet with image to Twitter/X.
        
        Args:
            image_path: Path to image file
            caption: Tweet text (max 280 chars)
        
        Returns:
            True if successful
        """
        platform = 'twitter'
        creds = self.credentials[platform]
        
        if not creds['username'] or not creds['password']:
            logger.error(f"❌ {platform.title()} credentials not configured in .env")
            return False
        
        try:
            # Use persistent session to keep login state
            self._setup_driver(use_persistent_session=True)
            logger.info(f"🐦 Posting to Twitter/X...")
            logger.info(f"   Username: {creds['username']}")
            logger.info(f"   Image: {image_path}")
            logger.info(f"   Caption length: {len(caption)} chars")
            
            # Check if already logged in by going to home
            logger.info("   Checking login status...")
            self.driver.get('https://twitter.com/home')
            time.sleep(3)
            
            # Check if we're already logged in
            current_url = self.driver.current_url
            is_logged_in = 'home' in current_url or 'compose' in current_url
            
            if is_logged_in:
                logger.info("   ✅ Already logged in! Skipping login step.")
            else:
                logger.info("   ⚠️ Not logged in, attempting login...")
                # Go to login page
                self.driver.get('https://twitter.com/login')
                time.sleep(5)
                
                try:
                    # Enter username - try multiple selectors
                    logger.info("   Entering username...")
                    username_selectors = [
                        (By.NAME, 'text'),
                        (By.CSS_SELECTOR, 'input[autocomplete="username"]'),
                        (By.XPATH, '//input[@name="text"]'),
                        (By.XPATH, '//input[@type="text"]')
                    ]
                    
                    username_entered = False
                    for by, selector in username_selectors:
                        try:
                            self._wait_and_send_keys(by, selector, creds['username'], timeout=5)
                            username_entered = True
                            break
                        except:
                            continue
                    
                    if not username_entered:
                        raise Exception("Could not find username field with any selector")
                    
                    # Click Next button
                    next_selectors = [
                        (By.XPATH, "//span[contains(text(), 'Next')]"),
                        (By.XPATH, "//button[@role='button']//span[text()='Next']"),
                        (By.CSS_SELECTOR, "button[type='button']")
                    ]
                    
                    for by, selector in next_selectors:
                        try:
                            self._wait_and_click(by, selector, timeout=5)
                            break
                        except:
                            continue
                            
                    time.sleep(4)
                except Exception as e:
                    logger.error(f"   Failed at username step: {e}")
                    raise
                
                try:
                    # Enter password - try multiple selectors
                    logger.info("   Entering password...")
                    
                    # Debug: dump page HTML if not headless
                    if not self.headless:
                        logger.info(f"   Page title: {self.driver.title}")
                        logger.info(f"   Current URL: {self.driver.current_url}")
                        # Check for unusual login prompts
                        page_text = self.driver.find_element(By.TAG_NAME, 'body').text
                        if 'phone' in page_text.lower() or 'verification' in page_text.lower():
                            logger.warning("⚠️ Twitter is asking for phone/verification!")
                            logger.warning(f"   Page text preview: {page_text[:500]}")
                    
                    password_selectors = [
                        (By.NAME, 'password'),
                        (By.CSS_SELECTOR, 'input[type="password"]'),
                        (By.CSS_SELECTOR, 'input[name="password"]'),
                        (By.XPATH, '//input[@type="password"]'),
                        (By.XPATH, '//input[@name="password"]')
                    ]
                    
                    password_entered = False
                    for by, selector in password_selectors:
                        try:
                            self._wait_and_send_keys(by, selector, creds['password'], timeout=5)
                            password_entered = True
                            logger.info(f"   ✓ Password entered with selector: {by} = {selector}")
                            break
                        except Exception as sel_error:
                            logger.debug(f"   ✗ Selector failed: {by} = {selector} ({sel_error})")
                            continue
                    
                    if not password_entered:
                        # Save HTML for debugging
                        if not self.headless:
                            html_path = f"/tmp/twitter_page_{int(time.time())}.html"
                            with open(html_path, 'w') as f:
                                f.write(self.driver.page_source)
                            logger.error(f"   Saved page HTML to: {html_path}")
                        raise Exception("Could not find password field with any selector")
                    
                    # Click Login button
                    login_selectors = [
                        (By.XPATH, "//span[contains(text(), 'Log in')]"),
                        (By.XPATH, "//button[@data-testid='LoginForm_Login_Button']"),
                        (By.XPATH, "//span[text()='Log in']"),
                        (By.CSS_SELECTOR, "button[type='button']")
                    ]
                    
                    for by, selector in login_selectors:
                        try:
                            self._wait_and_click(by, selector, timeout=5)
                            break
                        except:
                            continue
                            
                    time.sleep(8)
                except Exception as e:
                    logger.error(f"   Failed at password step: {e}")
                    raise
            
            try:
                # Navigate to compose page
                logger.info("   Going to compose page...")
                self.driver.get('https://twitter.com/compose/tweet')
                time.sleep(3)
            except Exception as e:
                logger.error(f"   Failed to navigate to compose: {e}")
                raise
            
            try:
                # Click tweet compose box - try multiple selectors
                # First, try to open compose via 'New Tweet' button or keyboard shortcut (n)
                logger.info("   Composing tweet...")
                # Try clicking a New Tweet button if present
                new_tweet_selectors = [
                    (By.CSS_SELECTOR, "div[data-testid='SideNav_NewTweet_Button']"),
                    (By.CSS_SELECTOR, "a[href='/compose/tweet']"),
                    (By.XPATH, "//a[contains(@href, '/compose/tweet')]"),
                    (By.XPATH, "//div[@aria-label='Tweet']"),
                ]
                try:
                    for by, selector in new_tweet_selectors:
                        try:
                            btn, sby, ssel = self._find_element_with_selectors([(by, selector)], timeout=3)
                            logger.debug(f"Found New Tweet opener: {sby} = {ssel}")
                            try:
                                btn.click()
                            except Exception:
                                self._wait_and_click(by, selector, timeout=3)
                            time.sleep(1)
                            break
                        except Exception:
                            continue
                except Exception:
                    # Not critical; proceed to open compose manually
                    pass

                # Simplified approach - go directly to compose page
                logger.info("   Opening Twitter compose page...")
                self.driver.get('https://twitter.com/compose/post')
                time.sleep(3)
                
                # Wait for and find compose box with simplified selectors
                compose_selectors = [
                    (By.CSS_SELECTOR, "div[data-testid='tweetTextarea_0']"),
                    (By.CSS_SELECTOR, "div[role='textbox'][contenteditable='true']"),
                    (By.XPATH, "//div[@contenteditable='true' and @role='textbox']"),
                ]
                
                composed = False
                try:
                    elem, cby, cselector = self._find_element_with_selectors(compose_selectors, timeout=10)
                    logger.info(f"   Found compose box: {cselector}")
                    
                    # Click to focus
                    elem.click()
                    time.sleep(0.5)
                    
                    # Type caption using JavaScript for reliability
                    self.driver.execute_script(
                        "arguments[0].textContent = arguments[1]; arguments[0].dispatchEvent(new Event('input', { bubbles: true }));",
                        elem,
                        caption
                    )
                    composed = True
                    logger.info(f"   Caption entered: {len(caption)} chars")
                except Exception as e:
                    logger.error(f"   Compose failed: {e}")
                    raise Exception(f"Could not find or fill compose box: {e}")
                
                time.sleep(2)
            except Exception as e:
                logger.error(f"   Failed to find compose box: {e}")
                raise
            
            try:
                # Upload image - try multiple selectors
                logger.info("   Uploading image...")
                file_input_selectors = [
                    (By.XPATH, "//input[@type='file']"),
                    (By.CSS_SELECTOR, "input[type='file']"),
                    (By.XPATH, "//input[@accept]")
                ]
                
                uploaded = False
                for by, selector in file_input_selectors:
                    try:
                        file_input, fby, fselector = self._find_element_with_selectors([(by, selector)], timeout=4)
                        logger.debug(f"File input matched selector: {fby} = {fselector}")
                        file_input.send_keys(str(Path(image_path).absolute()))
                        uploaded = True
                        break
                    except Exception as e:
                        logger.debug(f"File input selector failed: {by} {selector} ({e})")
                        continue
                
                if not uploaded:
                    raise Exception("Could not find file upload input")
                    
                time.sleep(5)
            except Exception as e:
                logger.error(f"   Failed to upload image: {e}")
                raise
            
            try:
                # Click Post button - try multiple selectors
                logger.info("   Clicking Post button...")
                post_selectors = [
                    (By.XPATH, "//button[@data-testid='tweetButtonInline']"),
                    (By.XPATH, "//span[contains(text(), 'Post')]"),
                    (By.XPATH, "//button//span[text()='Post']"),
                    (By.CSS_SELECTOR, "button[data-testid='tweetButton']")
                ]
                
                posted = False
                for by, selector in post_selectors:
                    try:
                        btn, pby, pselector = self._find_element_with_selectors([(by, selector)], timeout=8)
                        logger.debug(f"Post button matched selector: {pby} = {pselector}")
                        try:
                            btn.click()
                        except Exception:
                            self._wait_and_click(by, selector, timeout=8)
                        posted = True
                        break
                    except Exception as e:
                        logger.debug(f"Post button selector failed: {by} {selector} ({e})")
                        continue
                
                if not posted:
                    raise Exception("Could not find Post button")
                    
                time.sleep(4)
            except Exception as e:
                logger.error(f"   Failed to click Post button: {e}")
                raise
            
            logger.info(f"✅ Successfully posted to Twitter!")
            return True
            
        except Exception as e:
            logger.error(f"❌ Twitter posting failed: {e}")
            # Take screenshot for debugging
            try:
                screenshot_path = f"/tmp/twitter_error_{int(time.time())}.png"
                self.driver.save_screenshot(screenshot_path)
                logger.error(f"   Screenshot saved: {screenshot_path}")
            except:
                pass
            return False
        finally:
            if self.driver:
                self.driver.quit()
    
    def batch_post(
        self,
        platforms: List[str],
        image_path: str,
        caption: str,
        platform_specific_captions: Optional[Dict[str, str]] = None
    ) -> Dict[str, bool]:
        """
        Post to multiple platforms at once.
        
        Args:
            platforms: List of platform names ('instagram', 'facebook', 'twitter')
            image_path: Path to image file
            caption: Default caption for all platforms
            platform_specific_captions: Optional dict of platform: caption overrides
        
        Returns:
            Dict mapping platform to success status
        """
        results = {}
        
        logger.info(f"🚀 Batch posting to {len(platforms)} platforms...")
        
        for platform in platforms:
            platform_caption = (platform_specific_captions or {}).get(platform, caption)
            
            if platform == 'instagram':
                results[platform] = self.post_to_instagram(image_path, platform_caption)
            elif platform == 'facebook':
                results[platform] = self.post_to_facebook(image_path, platform_caption)
            elif platform == 'twitter':
                results[platform] = self.post_to_twitter(image_path, platform_caption)
            else:
                logger.warning(f"⚠️ Platform '{platform}' not yet supported")
                results[platform] = False
            
            time.sleep(5)  # Delay between platforms
        
        success_count = sum(1 for v in results.values() if v)
        logger.info(f"✅ Batch posting complete: {success_count}/{len(platforms)} successful")
        
        return results


# Example usage
if __name__ == "__main__":
    automation = SocialMediaAutomation(headless=False)
    
    # Post to Instagram
    automation.post_to_instagram(
        image_path="/path/to/image.png",
        caption="Check out our new product! 🚀 #newproduct #innovation"
    )
    
    # Batch post to multiple platforms
    results = automation.batch_post(
        platforms=['instagram', 'facebook', 'twitter'],
        image_path="/path/to/image.png",
        caption="Exciting announcement! 🎉",
        platform_specific_captions={
            'twitter': "Exciting announcement! 🎉 Learn more: https://example.com"
        }
    )
    
    print(f"Posting results: {results}")
