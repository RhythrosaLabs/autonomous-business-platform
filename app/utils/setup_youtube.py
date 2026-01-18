#!/usr/bin/env python3
"""
🎬 YouTube API Setup - Super Simple Version
Run this script to set up YouTube credentials for auto-uploading videos
"""

import os
import sys
from pathlib import Path
import pickle
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

# YouTube API scope
SCOPES = ['https://www.googleapis.com/auth/youtube.upload']

def main():
    print("=" * 60)
    print("🎬 YouTube API Setup - Let's Get You Connected!")
    print("=" * 60)
    print()
    
    # Check for client_secret.json
    client_secret_path = Path(__file__).parent / 'client_secret.json'
    
    if not client_secret_path.exists():
        print("❌ STEP 1: Get your client_secret.json file")
        print()
        print("You need to:")
        print("1. Go to: https://console.cloud.google.com/")
        print("2. Create a new project (or select existing)")
        print("3. Enable 'YouTube Data API v3'")
        print("4. Go to Credentials → Create Credentials → OAuth 2.0 Client ID")
        print("5. Choose 'Desktop app' as application type")
        print("6. Download the JSON file")
        print("7. Rename it to 'client_secret.json'")
        print("8. Put it in this folder:", Path(__file__).parent)
        print()
        print("📖 Need detailed help? Check: YOUTUBE_SETUP_GUIDE.md")
        print()
        
        response = input("❓ Do you have client_secret.json ready? (y/n): ").lower()
        if response != 'y':
            print("\n👋 Come back when you have client_secret.json!")
            sys.exit(0)
        
        # Ask them to paste the path
        print("\n📁 Drag your downloaded client_secret.json file here and press Enter:")
        file_path = input().strip().replace("'", "").replace('"', '')
        
        if not os.path.exists(file_path):
            print(f"\n❌ Could not find file at: {file_path}")
            sys.exit(1)
        
        # Copy to current directory
        import shutil
        shutil.copy(file_path, client_secret_path)
        print(f"✅ Copied to {client_secret_path}")
    else:
        print("✅ Found client_secret.json")
    
    print()
    print("=" * 60)
    print("🔐 STEP 2: Authorize with your Google account")
    print("=" * 60)
    print()
    print("A browser window will open for you to:")
    print("1. Sign in to your Google account")
    print("2. Select the YouTube channel to use")
    print("3. Grant permission to upload videos")
    print()
    
    input("Press Enter to open browser and start authorization... ")
    
    try:
        # Start OAuth flow
        flow = InstalledAppFlow.from_client_secrets_file(
            str(client_secret_path),
            SCOPES
        )
        
        # This will open in your default browser (Atlas)
        # Using port=0 lets it pick any available port automatically
        credentials = flow.run_local_server(
            port=0,
            success_message="✅ Authorization successful! You can close this window and return to the terminal."
        )
        
        # Save credentials
        token_path = Path(__file__).parent / 'token.pickle'
        with open(token_path, 'wb') as token_file:
            pickle.dump(credentials, token_file)
        
        print()
        print("=" * 60)
        print("🎉 SUCCESS! YouTube API is ready!")
        print("=" * 60)
        print()
        print("✅ Credentials saved to: token.pickle")
        print("✅ You can now auto-upload videos to YouTube!")
        print()
        print("📝 Your campaign generator will now be able to:")
        print("   - Upload videos automatically")
        print("   - Add titles and descriptions")
        print("   - Set thumbnails")
        print("   - Schedule publish times")
        print()
        print("🚀 Run your Streamlit app and try the YouTube auto-upload!")
        print()
        
    except Exception as e:
        print()
        print("=" * 60)
        print("❌ Authentication Failed")
        print("=" * 60)
        print()
        print(f"Error: {e}")
        print()
        print("Common issues:")
        print("- Make sure you're using the correct Google account")
        print("- Check that YouTube Data API v3 is enabled")
        print("- Verify the OAuth consent screen is configured")
        print()
        sys.exit(1)

if __name__ == '__main__':
    main()
