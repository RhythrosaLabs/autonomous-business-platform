"""
Music Platform OAuth Connection Manager
Handles OAuth 2.0 flows for all supported music platforms
"""

import os
import json
import requests
import base64
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple
from pathlib import Path
import webbrowser
from urllib.parse import urlencode, parse_qs, urlparse

# ========================================
# OAUTH CONFIGURATION FOR ALL PLATFORMS
# ========================================

OAUTH_CONFIGS = {
    "spotify": {
        "name": "Spotify",
        "auth_url": "https://accounts.spotify.com/authorize",
        "token_url": "https://accounts.spotify.com/api/token",
        "api_base": "https://api.spotify.com/v1",
        "scopes": [
            "user-read-private",
            "user-read-email",
            "user-library-read",
            "user-library-modify",
            "playlist-read-private",
            "playlist-modify-public",
            "playlist-modify-private",
            "user-read-playback-state",
            "user-read-currently-playing"
        ],
        "requires_pkce": True,
        "client_id_env": "SPOTIFY_CLIENT_ID",
        "client_secret_env": "SPOTIFY_CLIENT_SECRET"
    },
    
    "apple_music": {
        "name": "Apple Music",
        "auth_url": "https://appleid.apple.com/auth/authorize",
        "token_url": "https://appleid.apple.com/auth/token",
        "api_base": "https://api.music.apple.com/v1",
        "scopes": ["music"],
        "requires_pkce": True,
        "client_id_env": "APPLE_MUSIC_CLIENT_ID",
        "client_secret_env": "APPLE_MUSIC_CLIENT_SECRET",
        "note": "Requires Apple Developer Team ID"
    },
    
    "youtube_music": {
        "name": "YouTube Music",
        "auth_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
        "api_base": "https://www.googleapis.com/youtube/v3",
        "scopes": [
            "https://www.googleapis.com/auth/youtube",
            "https://www.googleapis.com/auth/youtube.upload"
        ],
        "requires_pkce": True,
        "client_id_env": "YOUTUBE_CLIENT_ID",
        "client_secret_env": "YOUTUBE_CLIENT_SECRET"
    },
    
    "soundcloud": {
        "name": "SoundCloud",
        "auth_url": "https://soundcloud.com/oauth/authorize",
        "token_url": "https://api.soundcloud.com/oauth2/token",
        "api_base": "https://api.soundcloud.com/v2",
        "scopes": ["non-expiring"],
        "requires_pkce": False,
        "client_id_env": "SOUNDCLOUD_CLIENT_ID",
        "client_secret_env": "SOUNDCLOUD_CLIENT_SECRET"
    },
    
    "deezer": {
        "name": "Deezer",
        "auth_url": "https://connect.deezer.com/oauth/auth.php",
        "token_url": "https://connect.deezer.com/oauth/token.php",
        "api_base": "https://api.deezer.com",
        "scopes": ["basic_access", "email", "offline_access"],
        "requires_pkce": False,
        "client_id_env": "DEEZER_CLIENT_ID",
        "client_secret_env": "DEEZER_CLIENT_SECRET",
        "note": "Uses Redirect URI with hash fragment"
    },
    
    "bandcamp": {
        "name": "Bandcamp",
        "auth_url": "https://bandcamp.com/oauth_authorize",
        "token_url": "https://bandcamp.com/api/oauth2/token",
        "api_base": "https://api.bandcamp.com",
        "scopes": ["artist", "fan"],
        "requires_pkce": False,
        "client_id_env": "BANDCAMP_CLIENT_ID",
        "client_secret_env": "BANDCAMP_CLIENT_SECRET",
        "note": "Requires manual approval"
    },
    
    "tiktok": {
        "name": "TikTok",
        "auth_url": "https://www.tiktok.com/oauth/authorize",
        "token_url": "https://open.tiktokapis.com/v2/oauth/token/",
        "api_base": "https://open.tiktokapis.com/v2",
        "scopes": ["user.info.basic", "video.list"],
        "requires_pkce": True,
        "client_id_env": "TIKTOK_CLIENT_ID",
        "client_secret_env": "TIKTOK_CLIENT_SECRET"
    },
    
    "amazon_music": {
        "name": "Amazon Music",
        "auth_url": "https://www.amazon.com/ap/oa",
        "token_url": "https://api.amazon.com/auth/o2/token",
        "api_base": "https://musicgremlin.amazon.com/api",
        "scopes": ["profile", "alexa::skills:ask:skil"],
        "requires_pkce": True,
        "client_id_env": "AMAZON_MUSIC_CLIENT_ID",
        "client_secret_env": "AMAZON_MUSIC_CLIENT_SECRET"
    },
    
    "tidal": {
        "name": "Tidal",
        "auth_url": "https://login.tidal.com/authorize",
        "token_url": "https://login.tidal.com/oauth2/token",
        "api_base": "https://api.tidal.com/v1",
        "scopes": ["r_usr", "w_usr"],
        "requires_pkce": False,
        "client_id_env": "TIDAL_CLIENT_ID",
        "client_secret_env": "TIDAL_CLIENT_SECRET"
    }
}

# ========================================
# OAUTH STATE MANAGER
# ========================================

class OAuthStateManager:
    """Manages OAuth state tokens and PKCE challenges"""
    
    def __init__(self, state_dir: str = "/tmp/oauth_states"):
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(exist_ok=True)
    
    def generate_state(self, platform: str) -> Tuple[str, Dict]:
        """Generate OAuth state with PKCE if needed"""
        state = secrets.token_urlsafe(32)
        
        state_data = {
            "state": state,
            "platform": platform,
            "created_at": datetime.now().isoformat(),
            "expires_at": (datetime.now() + timedelta(minutes=15)).isoformat()
        }
        
        # Add PKCE challenge if required
        if OAUTH_CONFIGS[platform].get("requires_pkce"):
            code_verifier = base64.urlsafe_b64encode(os.urandom(32)).decode('utf-8').rstrip('=')
            code_challenge = base64.urlsafe_b64encode(
                hashlib.sha256(code_verifier.encode()).digest()
            ).decode('utf-8').rstrip('=')
            
            state_data["code_verifier"] = code_verifier
            state_data["code_challenge"] = code_challenge
        
        # Save state
        state_file = self.state_dir / f"{state}.json"
        with open(state_file, 'w') as f:
            json.dump(state_data, f)
        
        return state, state_data
    
    def verify_state(self, state: str) -> Optional[Dict]:
        """Verify state token and return data"""
        state_file = self.state_dir / f"{state}.json"
        
        if not state_file.exists():
            return None
        
        try:
            with open(state_file) as f:
                state_data = json.load(f)
            
            # Check expiry
            expires_at = datetime.fromisoformat(state_data["expires_at"])
            if datetime.now() > expires_at:
                state_file.unlink()  # Delete expired state
                return None
            
            return state_data
        except Exception as e:
            print(f"Error verifying state: {e}")
            return None
    
    def cleanup_state(self, state: str):
        """Remove state file after use"""
        state_file = self.state_dir / f"{state}.json"
        if state_file.exists():
            state_file.unlink()

# ========================================
# OAUTH CONNECTION HANDLER
# ========================================

class MusicPlatformOAuthHandler:
    """Handles OAuth flows for music platforms"""
    
    def __init__(self, redirect_uri: str = "http://localhost:8502/oauth/callback"):
        self.redirect_uri = redirect_uri
        self.state_manager = OAuthStateManager()
        # Load .env file dynamically
        self._load_env_file()
    
    def _load_env_file(self):
        """Load environment variables from .env file"""
        env_file = Path('/Users/sheils/repos/printify/.env')
        if env_file.exists():
            try:
                with open(env_file) as f:
                    for line in f:
                        line = line.strip()
                        if line and '=' in line and not line.startswith('#'):
                            key, val = line.split('=', 1)
                            if key not in os.environ:  # Don't override already set vars
                                os.environ[key] = val.strip('"\'')  # Remove quotes if present
            except Exception:
                pass  # Silently fail if .env can't be read
    
    def get_authorization_url(self, platform: str, redirect_uri: Optional[str] = None) -> str:
        """Generate authorization URL for platform"""
        if platform not in OAUTH_CONFIGS:
            raise ValueError(f"Unknown platform: {platform}")
        
        config = OAUTH_CONFIGS[platform]
        client_id = os.getenv(config["client_id_env"])
        
        if not client_id:
            raise ValueError(f"Missing {config['client_id_env']} environment variable")
        
        state, state_data = self.state_manager.generate_state(platform)
        
        params = {
            "client_id": client_id,
            "redirect_uri": redirect_uri or self.redirect_uri,
            "response_type": "code",
            "state": state,
            "scope": " ".join(config["scopes"])
        }
        
        # Add PKCE challenge if required
        if config.get("requires_pkce"):
            params["code_challenge"] = state_data.get("code_challenge")
            params["code_challenge_method"] = "S256"
        
        # Platform-specific parameters
        if platform == "apple_music":
            params["response_mode"] = "form_post"
        
        auth_url = config["auth_url"]
        return f"{auth_url}?{urlencode(params)}", state
    
    def exchange_code_for_token(
        self, 
        platform: str, 
        code: str, 
        state: str,
        redirect_uri: Optional[str] = None
    ) -> Dict:
        """Exchange authorization code for access token"""
        
        if platform not in OAUTH_CONFIGS:
            raise ValueError(f"Unknown platform: {platform}")
        
        # Verify state
        state_data = self.state_manager.verify_state(state)
        if not state_data:
            raise ValueError("Invalid or expired state")
        
        config = OAUTH_CONFIGS[platform]
        client_id = os.getenv(config["client_id_env"])
        client_secret = os.getenv(config["client_secret_env"])
        
        if not client_id or not client_secret:
            raise ValueError(f"Missing OAuth credentials for {platform}")
        
        token_data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri or self.redirect_uri,
            "client_id": client_id,
            "client_secret": client_secret
        }
        
        # Add PKCE verifier if required
        if config.get("requires_pkce"):
            token_data["code_verifier"] = state_data.get("code_verifier")
        
        try:
            response = requests.post(
                config["token_url"],
                data=token_data,
                timeout=10
            )
            response.raise_for_status()
            
            token_response = response.json()
            
            # Standardize response
            result = {
                "access_token": token_response.get("access_token"),
                "token_type": token_response.get("token_type", "Bearer"),
                "expires_in": token_response.get("expires_in"),
                "refresh_token": token_response.get("refresh_token"),
                "scope": token_response.get("scope"),
                "platform": platform,
                "obtained_at": datetime.now().isoformat()
            }
            
            # Clean up state
            self.state_manager.cleanup_state(state)
            
            return result
            
        except requests.RequestException as e:
            raise Exception(f"Token exchange failed: {str(e)}")
    
    def refresh_access_token(self, platform: str, refresh_token: str) -> Dict:
        """Refresh an access token"""
        
        if platform not in OAUTH_CONFIGS:
            raise ValueError(f"Unknown platform: {platform}")
        
        config = OAUTH_CONFIGS[platform]
        client_id = os.getenv(config["client_id_env"])
        client_secret = os.getenv(config["client_secret_env"])
        
        if not client_id or not client_secret:
            raise ValueError(f"Missing OAuth credentials for {platform}")
        
        token_data = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": client_id,
            "client_secret": client_secret
        }
        
        try:
            response = requests.post(
                config["token_url"],
                data=token_data,
                timeout=10
            )
            response.raise_for_status()
            
            token_response = response.json()
            
            result = {
                "access_token": token_response.get("access_token"),
                "token_type": token_response.get("token_type", "Bearer"),
                "expires_in": token_response.get("expires_in"),
                "refresh_token": token_response.get("refresh_token", refresh_token),
                "platform": platform,
                "obtained_at": datetime.now().isoformat()
            }
            
            return result
            
        except requests.RequestException as e:
            raise Exception(f"Token refresh failed: {str(e)}")

# ========================================
# API CLIENT FOR EACH PLATFORM
# ========================================

class SpotifyAPIClient:
    """Spotify API client"""
    
    def __init__(self, access_token: str):
        self.access_token = access_token
        self.base_url = "https://api.spotify.com/v1"
        self.headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
    
    def get_current_user(self) -> Dict:
        """Get current user profile"""
        response = requests.get(
            f"{self.base_url}/me",
            headers=self.headers
        )
        return response.json()
    
    def get_top_tracks(self, limit: int = 10) -> Dict:
        """Get user's top tracks"""
        response = requests.get(
            f"{self.base_url}/me/top/tracks",
            headers=self.headers,
            params={"limit": limit}
        )
        return response.json()
    
    def get_saved_tracks(self, limit: int = 50) -> Dict:
        """Get user's saved tracks"""
        response = requests.get(
            f"{self.base_url}/me/tracks",
            headers=self.headers,
            params={"limit": limit}
        )
        return response.json()
    
    def create_playlist(self, name: str, description: str = "") -> Dict:
        """Create new playlist"""
        user_id = self.get_current_user()["id"]
        
        payload = {
            "name": name,
            "description": description,
            "public": False
        }
        
        response = requests.post(
            f"{self.base_url}/users/{user_id}/playlists",
            headers=self.headers,
            json=payload
        )
        return response.json()

class AppleMusicAPIClient:
    """Apple Music API client"""
    
    def __init__(self, access_token: str):
        self.access_token = access_token
        self.base_url = "https://api.music.apple.com/v1"
        self.headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
    
    def get_me(self) -> Dict:
        """Get current user"""
        response = requests.get(
            f"{self.base_url}/me",
            headers=self.headers
        )
        return response.json()

class YouTubeMusicAPIClient:
    """YouTube Music API client"""
    
    def __init__(self, access_token: str):
        self.access_token = access_token
        self.base_url = "https://www.googleapis.com/youtube/v3"
        self.headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
    
    def upload_video(self, file_path: str, metadata: Dict) -> Dict:
        """Upload video to YouTube"""
        # Requires separate upload implementation
        pass

class SoundCloudAPIClient:
    """SoundCloud API client"""
    
    def __init__(self, access_token: str):
        self.access_token = access_token
        self.base_url = "https://api.soundcloud.com/v2"
        self.headers = {
            "Authorization": f"OAuth {access_token}"
        }
    
    def get_me(self) -> Dict:
        """Get current user"""
        response = requests.get(
            f"{self.base_url}/me",
            headers=self.headers
        )
        return response.json()
    
    def get_my_tracks(self) -> Dict:
        """Get user's tracks"""
        response = requests.get(
            f"{self.base_url}/me/tracks",
            headers=self.headers
        )
        return response.json()

class DeezerAPIClient:
    """Deezer API client"""
    
    def __init__(self, access_token: str):
        self.access_token = access_token
        self.base_url = "https://api.deezer.com"
    
    def get_me(self) -> Dict:
        """Get current user"""
        response = requests.get(
            f"{self.base_url}/user/me",
            params={"access_token": self.access_token}
        )
        return response.json()

# ========================================
# CREDENTIAL STORAGE
# ========================================

class CredentialStorage:
    """Securely store and retrieve OAuth credentials"""
    
    def __init__(self, storage_dir: str = "/tmp/music_credentials"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(exist_ok=True)
    
    def save_credentials(self, platform: str, user_id: str, token_data: Dict):
        """Save OAuth credentials"""
        cred_file = self.storage_dir / f"{platform}_{user_id}.json"
        
        # Add timestamps
        token_data["saved_at"] = datetime.now().isoformat()
        token_data["user_id"] = user_id
        
        with open(cred_file, 'w') as f:
            json.dump(token_data, f)
        
        return cred_file
    
    def load_credentials(self, platform: str, user_id: str) -> Optional[Dict]:
        """Load OAuth credentials"""
        cred_file = self.storage_dir / f"{platform}_{user_id}.json"
        
        if not cred_file.exists():
            return None
        
        try:
            with open(cred_file) as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading credentials: {e}")
            return None
    
    def list_platforms(self, user_id: str) -> list:
        """List all connected platforms for user"""
        platforms = []
        for cred_file in self.storage_dir.glob(f"*_{user_id}.json"):
            platform = cred_file.stem.split("_")[0]
            platforms.append(platform)
        return platforms

# ========================================
# TEST HELPERS
# ========================================

def test_oauth_flow(platform: str):
    """Test OAuth flow for a platform"""
    handler = MusicPlatformOAuthHandler()
    
    try:
        # Step 1: Generate auth URL
        auth_url, state = handler.get_authorization_url(platform)
        print(f"✅ Authorization URL generated")
        print(f"🔗 Visit: {auth_url}")
        print(f"📝 State: {state}")
        
        # Step 2: User would authorize and get code
        # (This is manual in testing)
        
        return auth_url, state
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return None, None

if __name__ == "__main__":
    print("🎵 Music Platform OAuth Manager")
    print("Supported platforms:")
    for platform in OAUTH_CONFIGS.keys():
        print(f"  - {platform}")
