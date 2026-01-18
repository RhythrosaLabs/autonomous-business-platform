"""
YouTube Upload Helper
Handles OAuth 2.0 authentication and automated video uploads with retry logic.
Extracted from youtube-automate scripts for integration with autonomous_business_platform.py
"""

import os
import pickle
import datetime
import time
import httplib2
from pathlib import Path

from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError


# YouTube API Configuration
# Need upload, full youtube, and readonly scopes for full functionality
SCOPES = [
    'https://www.googleapis.com/auth/youtube.upload',
    'https://www.googleapis.com/auth/youtube',
    'https://www.googleapis.com/auth/youtube.readonly'
]
API_SERVICE_NAME = 'youtube'
API_VERSION = 'v3'


def _check_scopes_match(credentials, required_scopes):
    """Check if credentials have all required scopes."""
    if not credentials or not hasattr(credentials, 'scopes') or not credentials.scopes:
        return True  # Can't check, assume OK
    
    cred_scopes = set(credentials.scopes)
    required = set(required_scopes)
    
    # Check if we have all required scopes
    missing = required - cred_scopes
    if missing:
        print(f"⚠️ Token missing scopes: {missing}")
        return False
    return True


def get_youtube_service(client_secrets_file=None, token_file=None):
    """
    Authenticates with YouTube API using OAuth 2.0 flow and returns the service object.
    
    Args:
        client_secrets_file: Path to client_secret.json from Google Cloud Console
        token_file: Path to store/retrieve token.pickle (default: same dir as client_secrets_file)
    
    Returns:
        YouTube API service object
    
    Raises:
        FileNotFoundError: If client_secrets_file doesn't exist
        Exception: For other authentication errors
    """
    import json
    
    # Default paths
    if not client_secrets_file:
        root_dir = Path(__file__).parent
        client_secrets_file = root_dir / 'client_secret.json'
    
    client_secrets_file = Path(client_secrets_file)
    
    # Create client_secret.json from environment variables if it doesn't exist
    if not client_secrets_file.exists():
        client_id = os.getenv('YOUTUBE_CLIENT_ID')
        client_secret = os.getenv('YOUTUBE_CLIENT_SECRET')
        
        if client_id and client_secret:
            print("📝 Creating client_secret.json from environment variables...")
            client_config = {
                "installed": {
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "redirect_uris": ["http://localhost"],
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token"
                }
            }
            try:
                with open(client_secrets_file, 'w') as f:
                    json.dump(client_config, f, indent=2)
                print(f"✅ Created {client_secrets_file} from environment variables")
            except Exception as e:
                print(f"⚠️ Could not create client_secret.json: {e}")
    
    if not token_file:
        token_file = client_secrets_file.parent / 'token.pickle'
    else:
        token_file = Path(token_file)
    
    credentials = None
    needs_new_auth = False
    
    # Check for existing token
    if token_file.exists():
        try:
            with open(token_file, 'rb') as token:
                credentials = pickle.load(token)
                print(f"✅ Loaded existing YouTube credentials from {token_file}")
                
                # Check if token has all required scopes
                if not _check_scopes_match(credentials, SCOPES):
                    print("🔄 Token needs scope upgrade - will request incremental authorization")
                    needs_new_auth = True
                    
        except Exception as e:
            print(f"⚠️ Could not load token file (may be corrupted): {e}")
            credentials = None
            # Delete corrupted token file
            try:
                token_file.unlink()
                print(f"🗑️ Deleted corrupted token file")
            except:
                pass
    
    # If no valid credentials or needs new auth for scopes, initiate OAuth flow
    if not credentials or not credentials.valid or needs_new_auth:
        if credentials and credentials.expired and credentials.refresh_token and not needs_new_auth:
            try:
                print("🔄 Refreshing expired YouTube credentials...")
                credentials.refresh(Request())
                print("✅ Credentials refreshed successfully")
            except Exception as e:
                print(f"⚠️ Token refresh failed: {e}")
                print("🔐 Starting new OAuth flow...")
                credentials = None  # Force new OAuth flow
        
        if not credentials or needs_new_auth:
            if not client_secrets_file.exists():
                raise FileNotFoundError(
                    f"'{client_secrets_file}' not found. "
                    "Download from Google Cloud Console: "
                    "https://console.cloud.google.com/apis/credentials"
                )
            print("🔐 Starting YouTube OAuth flow...")
            flow = InstalledAppFlow.from_client_secrets_file(str(client_secrets_file), SCOPES)
            credentials = flow.run_local_server(port=0)
        
        # Save credentials for future runs
        try:
            with open(token_file, 'wb') as token:
                pickle.dump(credentials, token)
            print(f"✅ YouTube credentials saved to {token_file}")
        except Exception as e:
            print(f"⚠️ Could not save credentials: {e}")
            print("💡 Check file permissions for:", token_file)
    
    return build(API_SERVICE_NAME, API_VERSION, credentials=credentials)


def upload_to_youtube_legacy(
    video_path,
    title,
    description,
    tags=None,
    category_id='22',  # People & Blogs by default
    privacy_status='private',
    scheduled_publish_date=None,
    thumbnail_path=None,
    client_secrets_file=None,
    token_file=None,
    max_retries=5,
    initial_delay_seconds=1
):
    """
    Uploads a video to YouTube with robust error handling and retry logic.
    (Legacy function - see upload_to_youtube for simpler Streamlit integration)
    
    Args:
        video_path: Path to video file to upload
        title: Video title (max 100 characters)
        description: Video description (max 5000 characters)
        tags: List of tags (max 500 characters total)
        category_id: YouTube category ID
            1: Film & Animation
            10: Music
            22: People & Blogs (default)
            23: Comedy
            24: Entertainment
            25: News & Politics
            26: Howto & Style
            27: Education
            28: Science & Technology
        privacy_status: 'public', 'private', or 'unlisted'
        scheduled_publish_date: ISO 8601 datetime string (e.g., "2024-01-15T10:00:00Z")
        thumbnail_path: Path to thumbnail image (1280x720, max 2MB)
        client_secrets_file: Path to client_secret.json
        token_file: Path to token.pickle
        max_retries: Maximum retry attempts for transient errors
        initial_delay_seconds: Initial delay for exponential backoff
    
    Returns:
        video_id (str) if successful, None if failed
    """
    print(f"\n🚀 Uploading video to YouTube: {Path(video_path).name}")
    
    try:
        youtube = get_youtube_service(client_secrets_file, token_file)
    except Exception as e:
        print(f"❌ YouTube authentication failed: {e}")
        return None
    
    # Prepare video metadata
    body = {
        'snippet': {
            'title': title[:100],  # Enforce max length
            'description': description[:5000],  # Enforce max length
            'tags': tags or [],
            'categoryId': str(category_id)
        },
        'status': {
            'privacyStatus': privacy_status
        }
    }
    
    # Add scheduled publish date if provided
    if scheduled_publish_date:
        body['status']['publishAt'] = scheduled_publish_date
        if privacy_status == 'public':
            # Must be private initially for scheduling
            body['status']['privacyStatus'] = 'private'
    
    media_body = MediaFileUpload(video_path, chunksize=-1, resumable=True)
    
    # Retry loop for transient errors
    for attempt in range(max_retries):
        try:
            print(f"📤 Upload attempt {attempt + 1}/{max_retries}...")
            
            insert_request = youtube.videos().insert(
                part=','.join(body.keys()),
                body=body,
                media_body=media_body
            )
            
            # Upload with progress reporting
            response = None
            while response is None:
                status, response = insert_request.next_chunk()
                if status:
                    progress = int(status.progress() * 100)
                    print(f"  Upload progress: {progress}%")
            
            video_id = response['id']
            print(f"✅ Video uploaded: https://www.youtube.com/watch?v={video_id}")
            
            # Upload thumbnail if provided
            if thumbnail_path and Path(thumbnail_path).exists():
                print("🖼️  Uploading thumbnail...")
                try:
                    youtube.thumbnails().set(
                        videoId=video_id,
                        media_body=MediaFileUpload(thumbnail_path)
                    ).execute()
                    print("✅ Thumbnail uploaded successfully")
                except HttpError as e:
                    print(f"⚠️  Thumbnail upload failed (non-critical): {e}")
                except Exception as e:
                    print(f"⚠️  Unexpected thumbnail error: {e}")
            
            return video_id  # Success!
        
        except HttpError as e:
            # Retryable HTTP errors
            if e.resp.status in [500, 502, 503, 504, 429]:
                print(f"⚠️  Transient error ({e.resp.status}): {e}")
                if attempt < max_retries - 1:
                    delay = initial_delay_seconds * (2 ** attempt)
                    print(f"💤 Retrying in {delay:.1f} seconds...")
                    time.sleep(delay)
                else:
                    print(f"❌ Max retries reached. Upload failed.")
                    return None
            else:
                # Non-retryable errors (auth, quota, invalid request)
                print(f"❌ Permanent HTTP error ({e.resp.status}): {e}")
                return None
        
        except httplib2.HttpLib2Error as e:
            # Network errors
            print(f"⚠️  Network error: {e}")
            if attempt < max_retries - 1:
                delay = initial_delay_seconds * (2 ** attempt)
                print(f"💤 Retrying in {delay:.1f} seconds...")
                time.sleep(delay)
            else:
                print(f"❌ Max retries reached due to network issues.")
                return None
        
        except Exception as e:
            print(f"❌ Unexpected error during upload: {e}")
            return None
    
    return None


def generate_scheduled_publish_date(hours_from_now=2):
    """
    Generates an ISO 8601 formatted datetime string for scheduled publishing.
    
    Args:
        hours_from_now: Hours to add to current UTC time
    
    Returns:
        ISO 8601 datetime string (e.g., "2024-01-15T10:00:00Z")
    """
    publish_time = datetime.datetime.utcnow() + datetime.timedelta(hours=hours_from_now)
    return publish_time.isoformat("T") + "Z"


# Category mapping for convenience
YOUTUBE_CATEGORIES = {
    'Film & Animation': '1',
    'Autos & Vehicles': '2',
    'Music': '10',
    'Pets & Animals': '15',
    'Sports': '17',
    'Travel & Events': '19',
    'Gaming': '20',
    'People & Blogs': '22',
    'Comedy': '23',
    'Entertainment': '24',
    'News & Politics': '25',
    'Howto & Style': '26',
    'Education': '27',
    'Science & Technology': '28',
    'Nonprofits & Activism': '29'
}


def upload_to_youtube(youtube_service, video_path, metadata, thumbnail_path=None):
    """
    Simplified upload function for Streamlit page integration.
    
    Args:
        youtube_service: Authenticated YouTube API service object
        video_path: Path to video file
        metadata: Dict with keys: title, description, tags, category, privacy, notify_subscribers
        thumbnail_path: Optional path to thumbnail image
    
    Returns:
        Dict with video details including 'id' and 'url'
    """
    try:
        # Prepare body
        body = {
            'snippet': {
                'title': metadata['title'][:100],
                'description': metadata['description'][:5000],
                'tags': metadata.get('tags', []),
                'categoryId': str(metadata.get('category', '22'))
            },
            'status': {
                'privacyStatus': metadata.get('privacy', 'unlisted'),
                'selfDeclaredMadeForKids': False
            }
        }
        
        # Upload video
        media_body = MediaFileUpload(video_path, chunksize=-1, resumable=True)
        
        insert_request = youtube_service.videos().insert(
            part=','.join(body.keys()),
            body=body,
            media_body=media_body,
            notifySubscribers=metadata.get('notify_subscribers', False)
        )
        
        # Execute upload
        response = None
        while response is None:
            status, response = insert_request.next_chunk()
            if status:
                print(f"Upload progress: {int(status.progress() * 100)}%")
        
        video_id = response['id']
        
        # Upload thumbnail if provided
        if thumbnail_path and Path(thumbnail_path).exists():
            try:
                youtube_service.thumbnails().set(
                    videoId=video_id,
                    media_body=MediaFileUpload(thumbnail_path)
                ).execute()
                print("✅ Thumbnail uploaded")
            except Exception as e:
                print(f"⚠️ Thumbnail upload failed: {e}")
        
        return {
            'id': video_id,
            'url': f'https://youtube.com/watch?v={video_id}',
            'title': metadata['title'],
            'privacy': metadata.get('privacy', 'unlisted')
        }
        
    except Exception as e:
        print(f"❌ Upload failed: {e}")
        raise


if __name__ == "__main__":
    print("""
YouTube Helper Module
====================
This module provides YouTube upload functionality for autonomous_business_platform.py

Setup:
1. Go to https://console.cloud.google.com/apis/credentials
2. Create OAuth 2.0 Client ID (Desktop application)
3. Download client_secret.json and place in this directory
4. First run will open browser for authorization
5. Subsequent runs will use cached token.pickle

Example usage:
    from youtube_helper import get_youtube_service, upload_to_youtube
    
    youtube = get_youtube_service()
    result = upload_to_youtube(
        youtube_service=youtube,
        video_path="campaign_video.mp4",
        metadata={
            'title': "My Campaign Video",
            'description': "Created with autonomous platform",
            'tags': ["AI", "automation"],
            'category': '22',
            'privacy': 'unlisted',
            'notify_subscribers': False
        },
        thumbnail_path="thumbnail.jpg"
    )
    print(f"Video uploaded: {result['url']}")
""")
