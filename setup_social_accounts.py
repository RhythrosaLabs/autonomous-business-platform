#!/usr/bin/env python3
"""
Setup Social Media Accounts (TikTok & Pinterest)
================================================
This script helps you connect your TikTok and Pinterest accounts
that were created using "Sign up with Google".

Since both platforms use Google OAuth, we'll:
1. Use browser automation with your existing browser profile (you're already logged in!)
2. Verify the connection works
3. Test posting capability

Run with: python3 setup_social_accounts.py
"""

import os
import sys
import asyncio
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def print_banner():
    print("""
╔══════════════════════════════════════════════════════════════╗
║      🎵 TikTok & 📌 Pinterest Setup Wizard 🧙                 ║
║      Connect your Google-linked social accounts              ║
╚══════════════════════════════════════════════════════════════╝
    """)

def check_requirements():
    """Check if required packages are installed"""
    missing = []
    
    try:
        import browser_use
    except ImportError:
        missing.append('browser-use')
    
    try:
        from langchain_anthropic import ChatAnthropic
    except ImportError:
        missing.append('langchain-anthropic')
    
    try:
        import playwright
    except ImportError:
        missing.append('playwright')
    
    if missing:
        print(f"❌ Missing packages: {', '.join(missing)}")
        print(f"\nInstall with:")
        print(f"  pip install {' '.join(missing)}")
        if 'playwright' in missing:
            print(f"  playwright install chromium")
        return False
    
    # Check for Anthropic API key
    if not os.getenv('ANTHROPIC_API_KEY'):
        print("❌ ANTHROPIC_API_KEY not found in .env")
        print("   This is required for AI-powered browser automation")
        return False
    
    print("✅ All requirements satisfied")
    return True

def get_browser_type():
    """Get the browser type from env or ask user"""
    browser_type = os.getenv('BROWSER_TYPE', 'brave')
    
    print(f"\n🌐 Current browser setting: {browser_type}")
    print("   Options: brave, chrome, firefox")
    
    user_input = input(f"   Press Enter to use '{browser_type}' or type a different browser: ").strip().lower()
    
    if user_input in ['brave', 'chrome', 'firefox']:
        browser_type = user_input
    elif user_input:
        print(f"   Invalid browser '{user_input}', using '{browser_type}'")
    
    return browser_type

async def verify_login(browser_type: str, platform: str):
    """Open browser and verify user is logged in to the platform"""
    from browser_use import Browser, BrowserConfig
    
    urls = {
        'tiktok': 'https://www.tiktok.com/upload',
        'pinterest': 'https://www.pinterest.com/pin-builder/'
    }
    
    browser_paths = {
        'chrome': '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
        'brave': '/Applications/Brave Browser.app/Contents/MacOS/Brave Browser',
        'firefox': '/Applications/Firefox.app/Contents/MacOS/firefox',
    }
    
    browser_path = browser_paths.get(browser_type, browser_paths['brave'])
    automation_profile = os.path.expanduser(f'~/.browser-use-{browser_type}-profile')
    
    print(f"\n🔍 Checking {platform.title()} login status...")
    print(f"   Opening {platform.title()} in {browser_type}...")
    print(f"   Profile: {automation_profile}")
    
    config = BrowserConfig(
        headless=False,  # Show the browser so user can log in if needed
        chrome_instance_path=browser_path,
        extra_chromium_args=[
            f'--user-data-dir={automation_profile}',
            '--no-first-run',
            '--no-default-browser-check',
            '--disable-blink-features=AutomationControlled',
        ]
    )
    
    browser = Browser(config=config)
    
    try:
        context = await browser.new_context()
        page = await context.new_page()
        
        await page.goto(urls[platform])
        
        print(f"\n   ✨ Browser opened to {platform.title()}")
        print(f"   👀 Please check if you're logged in.")
        print(f"   📱 If not logged in, click 'Continue with Google' to sign in.")
        
        input(f"\n   Press Enter when you've verified you're logged in to {platform.title()}...")
        
        # Take a screenshot for verification
        screenshot_path = Path(f"temp_files/{platform}_login_check.png")
        screenshot_path.parent.mkdir(exist_ok=True)
        await page.screenshot(path=str(screenshot_path))
        print(f"   📸 Screenshot saved to {screenshot_path}")
        
        await browser.close()
        return True
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        try:
            await browser.close()
        except:
            pass
        return False

async def test_post(browser_type: str, platform: str):
    """Test posting capability (dry run)"""
    from browser_use import Agent, Browser, BrowserConfig
    from langchain_anthropic import ChatAnthropic
    from pydantic import SecretStr
    
    print(f"\n🧪 Testing {platform.title()} posting capability...")
    
    browser_paths = {
        'chrome': '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
        'brave': '/Applications/Brave Browser.app/Contents/MacOS/Brave Browser',
        'firefox': '/Applications/Firefox.app/Contents/MacOS/firefox',
    }
    
    browser_path = browser_paths.get(browser_type, browser_paths['brave'])
    automation_profile = os.path.expanduser(f'~/.browser-use-{browser_type}-profile')
    
    config = BrowserConfig(
        headless=False,
        chrome_instance_path=browser_path,
        extra_chromium_args=[
            f'--user-data-dir={automation_profile}',
            '--no-first-run',
            '--no-default-browser-check',
            '--disable-blink-features=AutomationControlled',
        ]
    )
    
    browser = Browser(config=config)
    
    task = ""
    if platform == 'tiktok':
        task = """
        1. Navigate to https://www.tiktok.com/upload
        2. Verify that you can see the upload page (you should be logged in)
        3. Look for the upload button or drag-and-drop area
        4. Report what you see - can we upload content here?
        5. DO NOT actually upload anything, just verify access
        """
    elif platform == 'pinterest':
        task = """
        1. Navigate to https://www.pinterest.com/pin-builder/
        2. Verify that you can see the pin creation page (you should be logged in)
        3. Look for the image upload area
        4. Report what you see - can we create pins here?
        5. DO NOT actually create a pin, just verify access
        """
    
    api_key = os.getenv('ANTHROPIC_API_KEY')
    llm = ChatAnthropic(
        model_name="claude-sonnet-4-20250514",
        api_key=SecretStr(api_key),
        temperature=0,
    )
    
    agent = Agent(
        task=task,
        llm=llm,
        browser=browser,
    )
    
    try:
        print(f"   🤖 AI agent is checking {platform.title()}...")
        history = await agent.run(max_steps=10)
        
        print(f"   ✅ Test completed in {len(history.history)} steps")
        
        # Get the last message/result
        if history.history:
            last_action = history.history[-1]
            print(f"   📝 Result: {getattr(last_action, 'result', 'Check completed')}")
        
        await browser.close()
        return True
        
    except Exception as e:
        print(f"   ❌ Test failed: {e}")
        try:
            await browser.close()
        except:
            pass
        return False

def update_env_file(platform: str, google_email: str):
    """Update .env file with platform credentials"""
    env_path = Path('.env')
    
    if not env_path.exists():
        print("❌ .env file not found!")
        return False
    
    with open(env_path, 'r') as f:
        content = f.read()
    
    # For Google OAuth accounts, we use the Google email
    # The browser automation will handle the "Continue with Google" flow
    updates = {
        f'{platform.upper()}_USERNAME': google_email,
        f'{platform.upper()}_PASSWORD': 'GOOGLE_OAUTH',  # Marker that this uses Google Sign-In
    }
    
    for key, value in updates.items():
        # Check if key exists with empty value
        import re
        pattern = rf'^{key}=.*$'
        replacement = f'{key}={value}'
        
        if re.search(pattern, content, re.MULTILINE):
            content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
        else:
            # Key doesn't exist, we shouldn't add it (it should be in .env already)
            pass
    
    with open(env_path, 'w') as f:
        f.write(content)
    
    print(f"   ✅ Updated .env with {platform.title()} credentials")
    return True

async def main():
    print_banner()
    
    # Check requirements
    if not check_requirements():
        print("\n❌ Please install missing requirements and try again.")
        return
    
    # Get browser type
    browser_type = get_browser_type()
    
    # Get Google email (they use Google Sign-In)
    google_email = os.getenv('EMAIL_USERNAME', '')
    if not google_email:
        google_email = input("\n📧 Enter your Google email (used for sign-in): ").strip()
    else:
        print(f"\n📧 Using Google email from .env: {google_email}")
        confirm = input("   Press Enter to confirm or type a different email: ").strip()
        if confirm:
            google_email = confirm
    
    print("\n" + "="*60)
    print("📌 PINTEREST SETUP")
    print("="*60)
    
    print("\n1️⃣  First, let's verify your Pinterest login...")
    pinterest_ok = await verify_login(browser_type, 'pinterest')
    
    if pinterest_ok:
        print("\n2️⃣  Testing Pinterest posting capability...")
        test_result = await test_post(browser_type, 'pinterest')
        
        if test_result:
            update_env_file('pinterest', google_email)
            print("\n✅ Pinterest setup complete!")
        else:
            print("\n⚠️  Pinterest test had issues, but login may still work")
            update_env_file('pinterest', google_email)
    
    print("\n" + "="*60)
    print("🎵 TIKTOK SETUP")
    print("="*60)
    
    print("\n1️⃣  Now let's verify your TikTok login...")
    tiktok_ok = await verify_login(browser_type, 'tiktok')
    
    if tiktok_ok:
        print("\n2️⃣  Testing TikTok posting capability...")
        test_result = await test_post(browser_type, 'tiktok')
        
        if test_result:
            update_env_file('tiktok', google_email)
            print("\n✅ TikTok setup complete!")
        else:
            print("\n⚠️  TikTok test had issues, but login may still work")
            update_env_file('tiktok', google_email)
    
    print("\n" + "="*60)
    print("🎉 SETUP COMPLETE!")
    print("="*60)
    print("""
Your TikTok and Pinterest accounts are now configured!

The system uses browser automation to post content:
- It opens YOUR browser with YOUR logged-in profiles
- No API keys needed - it uses the "Continue with Google" flow
- Your credentials are stored for reference in .env

To post content:
1. Use the Dashboard → Campaign Creator → Select TikTok/Pinterest
2. Or use Otto: "Post this image to TikTok and Pinterest"
3. Or use the Video Producer with social sharing

Note: Make sure Brave/Chrome is not running when auto-posting starts.
""")

if __name__ == '__main__':
    asyncio.run(main())
