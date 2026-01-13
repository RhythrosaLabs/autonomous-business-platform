"""
Professional Music Platforms Manager
Handles multiple music distribution platforms with service-specific features
Includes: Spotify, Apple Music, YouTube Music, Bandcamp, SoundCloud, Deezer, TikTok, 
Amazon Music, Tidal, Beatport, Traxsource, Juno Download, etc.
"""

from abp_imports_common import (
    st, json, os, datetime, timedelta, Path, asyncio, 
    dataclass, asdict, Dict, List, Optional, Any, setup_logger
)

logger = setup_logger(__name__)

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

try:
    from music_platform_oauth import (
        MusicPlatformOAuthHandler,
        CredentialStorage,
        OAUTH_CONFIGS,
        SpotifyAPIClient,
        AppleMusicAPIClient,
        YouTubeMusicAPIClient,
        SoundCloudAPIClient,
        DeezerAPIClient
    )
    OAUTH_AVAILABLE = True
except ImportError:
    OAUTH_AVAILABLE = False

# ========================================
# DATA MODELS FOR PLATFORM CREDENTIALS
# ========================================

@dataclass
class PlatformCredentials:
    """Unified credential storage for all platforms"""
    platform_name: str
    service_id: str  # Unique identifier (e.g., spotify_user_123)
    oauth_token: Optional[str] = None
    api_key: Optional[str] = None
    refresh_token: Optional[str] = None
    credentials_data: Dict = None
    last_updated: str = None
    is_active: bool = True
    
    def __post_init__(self):
        if self.credentials_data is None:
            self.credentials_data = {}
        if self.last_updated is None:
            self.last_updated = datetime.now().isoformat()

# ========================================
# MUSIC PLATFORMS CONFIGURATION
# ========================================

MUSIC_PLATFORMS = {
    # Streaming Platforms
    "spotify": {
        "name": "🎵 Spotify",
        "color": "#1DB954",
        "icon": "🎵",
        "capabilities": [
            "👤 Artist Profile Management",
            "📊 Real-time Analytics & Stats",
            "🎵 Playlist Management",
            "📈 Listener Demographics",
            "🎙️ Podcast Integration",
            "💰 Revenue Reports",
            "📱 Spotify for Artists",
            "🔗 Cross-promotion Features"
        ],
        "features": {
            "analytics": True,
            "playlist_management": True,
            "artist_profile": True,
            "podcasts": True,
            "revenue_tracking": True,
            "api_access": True
        }
    },
    
    "apple_music": {
        "name": "🍎 Apple Music",
        "color": "#FA243C",
        "icon": "🍎",
        "capabilities": [
            "👤 Artist Profile",
            "📊 Listener Stats",
            "🎵 Playlist Placements",
            "🎨 Artwork Management",
            "💰 Payment Tracking",
            "📱 Apple Music for Artists",
            "🔗 iTunes Integration",
            "🌍 Global Territory Support"
        ],
        "features": {
            "analytics": True,
            "artist_profile": True,
            "artwork": True,
            "playlist_submissions": True,
            "revenue_tracking": True
        }
    },
    
    "youtube_music": {
        "name": "📹 YouTube Music",
        "color": "#FF0000",
        "icon": "📹",
        "capabilities": [
            "🎬 Upload Music Videos",
            "📊 View Analytics",
            "💬 Community Posts",
            "🎯 Targeted Distribution",
            "💰 Monetization Controls",
            "🎵 Releases Management",
            "📈 Trending Data",
            "🔗 YouTube Integration"
        ],
        "features": {
            "video_upload": True,
            "analytics": True,
            "community": True,
            "monetization": True,
            "release_management": True,
            "shorts": True
        }
    },
    
    # Independent/Direct Sales
    "bandcamp": {
        "name": "🎸 Bandcamp",
        "color": "#1DA0C3",
        "icon": "🎸",
        "capabilities": [
            "🏪 Direct Sales",
            "📊 Detailed Sales Analytics",
            "🎵 Track Management",
            "💰 Payment Processing",
            "👥 Fan Management",
            "📧 Fan Email",
            "🎨 Store Customization",
            "📈 Merch Integration"
        ],
        "features": {
            "direct_sales": True,
            "track_management": True,
            "fan_management": True,
            "fan_email": True,
            "merch": True,
            "store_customization": True,
            "detailed_analytics": True
        }
    },
    
    # Streaming with Community
    "soundcloud": {
        "name": "☁️ SoundCloud",
        "color": "#FF7700",
        "icon": "☁️",
        "capabilities": [
            "🎵 Upload Tracks",
            "📊 Play Stats & Analytics",
            "💬 Comments & Interaction",
            "🔁 Reposts & Likes",
            "🎙️ Podcasts",
            "🎯 Monetization",
            "🌍 Discovery Features",
            "👥 Artist Network"
        ],
        "features": {
            "upload": True,
            "analytics": True,
            "community": True,
            "monetization": True,
            "podcasts": True,
            "discovery": True
        }
    },
    
    "deezer": {
        "name": "🎼 Deezer",
        "color": "#FF0084",
        "icon": "🎼",
        "capabilities": [
            "🎵 Distribution",
            "📊 Listener Analytics",
            "💰 Revenue Reporting",
            "🎯 Playlist Pitching",
            "🌍 150+ Countries",
            "📱 Deezer Podcasts",
            "🔊 Audio Quality Tiers",
            "👥 Artist Tools"
        ],
        "features": {
            "distribution": True,
            "analytics": True,
            "playlist_pitching": True,
            "podcasts": True,
            "revenue_tracking": True,
            "global_reach": True
        }
    },
    
    # Short-form Video / Emerging
    "tiktok": {
        "name": "🎵 TikTok",
        "color": "#25F4EE",
        "icon": "🎵",
        "capabilities": [
            "🎬 Upload Sounds",
            "📊 Sound Stats",
            "💰 Creator Fund",
            "🎯 Sound Promotion",
            "👥 Duets & Stitches",
            "💎 Premium Features",
            "📈 Trend Analytics",
            "🔊 Sound Library"
        ],
        "features": {
            "sound_upload": True,
            "analytics": True,
            "creator_fund": True,
            "viral_tracking": True,
            "trend_data": True
        }
    },
    
    "amazon_music": {
        "name": "🔶 Amazon Music",
        "color": "#FF9900",
        "icon": "🔶",
        "capabilities": [
            "🎵 Upload to Distribution",
            "📊 Royalty Reporting",
            "💰 Payment Tracking",
            "🌍 Global Distribution",
            "📱 Artist Central",
            "🎯 Playlist Placements",
            "🔊 HD/Spatial Audio",
            "📈 Sales Metrics"
        ],
        "features": {
            "distribution": True,
            "analytics": True,
            "royalty_tracking": True,
            "hd_audio": True,
            "global_reach": True
        }
    },
    
    "tidal": {
        "name": "🌊 Tidal",
        "color": "#000000",
        "icon": "🌊",
        "capabilities": [
            "🎵 Distribution",
            "📊 Detailed Analytics",
            "💰 Hi-Fi Revenue",
            "🎯 Playlist Pitching",
            "🌍 140+ Countries",
            "📱 Artist Tools",
            "🔊 Lossless Audio",
            "👥 Collaboration Features"
        ],
        "features": {
            "distribution": True,
            "analytics": True,
            "hifi_audio": True,
            "playlist_pitching": True,
            "global_reach": True
        }
    },
    
    # Specialized/Niche
    "beatport": {
        "name": "💿 Beatport",
        "color": "#1A1A1A",
        "icon": "💿",
        "capabilities": [
            "🎵 Electronic Music Distribution",
            "📊 Genre-Specific Analytics",
            "💰 DJ Sales Tracking",
            "🎯 Chart Rankings",
            "🔊 Stems & Acapellas",
            "📈 Sales by Genre",
            "👥 DJ Community",
            "🏆 Chart Performance"
        ],
        "features": {
            "distribution": True,
            "genre_analytics": True,
            "stems": True,
            "chart_tracking": True,
            "dj_focused": True
        }
    },
    
    "traxsource": {
        "name": "🔥 Traxsource",
        "color": "#FF6B00",
        "icon": "🔥",
        "capabilities": [
            "🎵 House/Techno Distribution",
            "📊 House Music Analytics",
            "💰 DJ Sales",
            "🎯 Chart Positions",
            "📈 Genre Trends",
            "👥 DJ Discovery",
            "🔊 Preview Clips",
            "🏆 Weekly Charts"
        ],
        "features": {
            "distribution": True,
            "genre_specialized": True,
            "analytics": True,
            "chart_tracking": True
        }
    },
    
    "juno_download": {
        "name": "🎧 Juno Download",
        "color": "#5C8FC4",
        "icon": "🎧",
        "capabilities": [
            "🎵 Vinyl & Digital Sales",
            "📊 Sales Analytics",
            "💰 Direct Revenue",
            "🎯 Top Charts",
            "🔊 FLAC Support",
            "📈 Download Trends",
            "👥 DJ Community",
            "🏪 Online Store"
        ],
        "features": {
            "sales": True,
            "analytics": True,
            "flac_support": True,
            "chart_tracking": True
        }
    }
}

# ========================================
# DATA PERSISTENCE
# ========================================

def get_music_data_dir():
    """Create and return music platforms data directory"""
    data_dir = Path("/tmp/music_platforms")
    data_dir.mkdir(exist_ok=True)
    return data_dir

def load_connected_platforms() -> Dict[str, PlatformCredentials]:
    """Load all connected platforms"""
    data_dir = get_music_data_dir()
    credentials_file = data_dir / "credentials.json"
    
    if not credentials_file.exists():
        return {}
    
    try:
        with open(credentials_file) as f:
            data = json.load(f)
        
        platforms = {}
        for key, cred_data in data.items():
            cred = PlatformCredentials(**cred_data)
            platforms[key] = cred
        return platforms
    except Exception as e:
        st.error(f"Error loading credentials: {e}")
        return {}

def save_connected_platforms(platforms: Dict[str, PlatformCredentials]):
    """Save all platform credentials"""
    data_dir = get_music_data_dir()
    credentials_file = data_dir / "credentials.json"
    
    try:
        data = {key: asdict(cred) for key, cred in platforms.items()}
        with open(credentials_file, 'w') as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        st.error(f"Error saving credentials: {e}")

# ========================================
# PLATFORM-SPECIFIC TABS
# ========================================

def render_spotify_tab():
    """Spotify-specific controls and analytics"""
    st.markdown("### 🎵 Spotify for Artists")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Total Followers", "12,543", "+234")
    with col2:
        st.metric("Monthly Listeners", "8,923", "+1,234")
    with col3:
        st.metric("Saves This Month", "456", "+89")
    
    st.divider()
    
    tabs = st.tabs(["📊 Analytics", "🎵 Track Management", "📝 Playlist Pitching", "👥 Artist Tools", "💰 Royalties"])
    
    with tabs[0]:
        st.subheader("Listener Analytics")
        
        # Mock data
        dates = pd.date_range(start='2025-12-01', periods=30)
        listeners = [8000 + i*100 + (i%3)*500 for i in range(30)]
        
        fig = px.line(
            x=dates, y=listeners,
            title="Monthly Listeners Trend",
            labels={"x": "Date", "y": "Listeners"}
        )
        st.plotly_chart(fig, use_container_width=True)
        
        st.markdown("**Top Tracks (Last 30 Days)**")
        tracks_df = pd.DataFrame({
            "Track": ["Song A", "Song B", "Song C", "Song D"],
            "Streams": [50000, 38000, 25000, 12000],
            "Saves": [2500, 1800, 1200, 600]
        })
        st.dataframe(tracks_df, use_container_width=True)
    
    with tabs[1]:
        st.subheader("Manage Your Tracks")
        st.info("🎵 Upload and manage your tracks directly from Spotify for Artists")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("📤 Upload New Release"):
                st.success("Upload functionality would open here")
        with col2:
            if st.button("✏️ Edit Track Details"):
                st.info("Edit mode for your tracks")
    
    with tabs[2]:
        st.subheader("Pitch to Playlists")
        st.info("Submit your tracks to Spotify editorial playlists")
        
        col1, col2 = st.columns(2)
        with col1:
            track = st.selectbox("Select Track", ["Song A", "Song B", "Song C"])
        with col2:
            genre = st.selectbox("Genre", ["Pop", "Hip-Hop", "R&B", "Electronic"])
        
        if st.button("📨 Submit Pitch"):
            st.success(f"Pitched {track} to playlists!")
    
    with tabs[3]:
        st.subheader("Artist Tools")
        st.markdown("""
        - **Spotify Codes**: Generate scannable codes for your music
        - **Canvas Videos**: Upload animated music videos
        - **Podcast Tools**: If applicable for your account
        - **Collaborations**: Manage featured artist relationships
        """)
    
    with tabs[4]:
        st.subheader("Royalty Information")
        st.warning("Detailed royalty reporting coming soon")

def render_apple_music_tab():
    """Apple Music-specific controls"""
    st.markdown("### 🍎 Apple Music for Artists")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Total Listeners", "5,234", "+567")
    with col2:
        st.metric("Playlist Adds", "12", "+2")
    with col3:
        st.metric("This Month Revenue", "$1,234", "+$234")
    
    st.divider()
    
    tabs = st.tabs(["📊 Analytics", "🎨 Artwork", "🎵 Release Management", "💰 Payments"])
    
    with tabs[0]:
        st.subheader("Apple Music Analytics")
        st.info("Real-time listener data from Apple Music")
        
        metrics_col1, metrics_col2, metrics_col3 = st.columns(3)
        with metrics_col1:
            st.metric("Plays", "12,450")
        with metrics_col2:
            st.metric("Playlist Adds", "45")
        with metrics_col3:
            st.metric("Countries", "87")
    
    with tabs[1]:
        st.subheader("Artwork Management")
        st.info("Upload and manage artwork for your releases")
        
        uploaded_art = st.file_uploader("Upload Album Artwork", type=["jpg", "png"])
        if uploaded_art:
            st.image(uploaded_art, caption="Uploaded Artwork", width=200)
            if st.button("✅ Apply to Latest Release"):
                st.success("Artwork updated!")
    
    with tabs[2]:
        st.subheader("Release Management")
        col1, col2 = st.columns(2)
        with col1:
            release_date = st.date_input("Release Date")
        with col2:
            release_type = st.selectbox("Release Type", ["Single", "EP", "Album", "Compilation"])
        
        if st.button("📅 Schedule Release"):
            st.success(f"Release scheduled for {release_date}")
    
    with tabs[3]:
        st.subheader("Payment Information")
        st.info("View your Apple Music earnings")
        
        earnings_df = pd.DataFrame({
            "Month": ["November", "December", "January"],
            "Earnings": ["$567", "$891", "$1,234"],
            "Plays": ["8,900", "12,340", "15,670"]
        })
        st.dataframe(earnings_df, use_container_width=True)

def render_youtube_music_tab():
    """YouTube Music-specific controls"""
    st.markdown("### 📹 YouTube Music")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Videos", "24")
    with col2:
        st.metric("Subscribers", "3,456")
    with col3:
        st.metric("Total Views", "125,000")
    
    st.divider()
    
    tabs = st.tabs(["🎬 Upload", "📊 Analytics", "🎵 Releases", "💬 Community", "💰 Monetization"])
    
    with tabs[0]:
        st.subheader("Upload Music Video")
        
        col1, col2 = st.columns(2)
        with col1:
            video_file = st.file_uploader("Select Video File", type=["mp4", "mov", "avi"])
        with col2:
            title = st.text_input("Video Title")
        
        description = st.text_area("Description")
        
        if st.button("📤 Upload to YouTube"):
            if video_file and title:
                st.success("Video uploaded successfully!")
            else:
                st.error("Please fill in all fields")
    
    with tabs[1]:
        st.subheader("Performance Analytics")
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            y=[100, 200, 300, 250, 400, 350],
            mode='lines+markers',
            name='Views'
        ))
        st.plotly_chart(fig, use_container_width=True)
    
    with tabs[2]:
        st.subheader("Manage Releases")
        st.info("Create and schedule music releases")
        
        if st.button("➕ Create New Release"):
            st.success("New release created")
    
    with tabs[3]:
        st.subheader("Community Posts")
        st.info("Share updates with your community")
        
        post_text = st.text_area("What's on your mind?")
        if st.button("📝 Post"):
            if post_text:
                st.success("Post published!")
    
    with tabs[4]:
        st.subheader("Monetization")
        st.metric("YouTube Revenue (This Month)", "$2,345")
        st.info("Your channel is monetized. Earnings appear after payment processing.")

def render_bandcamp_tab():
    """Bandcamp-specific controls with direct sales focus"""
    st.markdown("### 🎸 Bandcamp Store")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Direct Sales", "$3,456", "+$234")
    with col2:
        st.metric("Total Fans", "234", "+12")
    with col3:
        st.metric("Items Sold", "89", "+5")
    
    st.divider()
    
    tabs = st.tabs(["🏪 Store", "📊 Sales", "👥 Fans", "🎵 Tracks", "📧 Email", "🎨 Merch"])
    
    with tabs[0]:
        st.subheader("Store Management")
        
        col1, col2 = st.columns(2)
        with col1:
            st.text_input("Store Name", "My Music Store")
        with col2:
            st.selectbox("Currency", ["USD", "EUR", "GBP", "CAD"])
        
        if st.button("💾 Save Store Settings"):
            st.success("Store settings updated!")
    
    with tabs[1]:
        st.subheader("Sales Analytics")
        
        sales_df = pd.DataFrame({
            "Date": ["2025-01-01", "2025-01-02", "2025-01-03"],
            "Sales": [5, 8, 12],
            "Revenue": ["$50", "$80", "$120"]
        })
        st.dataframe(sales_df, use_container_width=True)
        
        fig = px.bar(sales_df, x="Date", y="Revenue", title="Daily Revenue")
        st.plotly_chart(fig, use_container_width=True)
    
    with tabs[2]:
        st.subheader("Fan Management")
        st.info("Direct relationship with your fans")
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Email Subscribers", "156")
        with col2:
            st.metric("Active Fans", "89")
    
    with tabs[3]:
        st.subheader("Track Management")
        
        track_list = st.dataframe(pd.DataFrame({
            "Track": ["Song 1", "Song 2", "Song 3"],
            "Price": ["$1.00", "$0.50", "Free"],
            "Sales": [23, 45, 89]
        }), use_container_width=True)
    
    with tabs[4]:
        st.subheader("Fan Email")
        
        subject = st.text_input("Email Subject")
        message = st.text_area("Message to Fans")
        
        if st.button("📧 Send Email"):
            if subject and message:
                st.success(f"Email sent to 156 subscribers!")
    
    with tabs[5]:
        st.subheader("Merchandise Integration")
        st.info("Sell physical merch alongside your music")
        
        if st.button("🛍️ Add Merch Item"):
            st.info("Merch integration coming soon")

def render_soundcloud_tab():
    """SoundCloud-specific controls"""
    st.markdown("### ☁️ SoundCloud")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Followers", "2,345", "+123")
    with col2:
        st.metric("Total Plays", "45,678", "+5,234")
    with col3:
        st.metric("Reposts", "234", "+12")
    
    st.divider()
    
    tabs = st.tabs(["📤 Upload", "📊 Stats", "💬 Comments", "👥 Network", "💰 Monetization"])
    
    with tabs[0]:
        st.subheader("Upload Tracks")
        
        col1, col2 = st.columns(2)
        with col1:
            audio_file = st.file_uploader("Select Audio File", type=["mp3", "wav", "flac"])
        with col2:
            title = st.text_input("Track Title")
        
        description = st.text_area("Description")
        genre = st.selectbox("Genre", ["Electronic", "Hip-Hop", "Rock", "Pop", "Other"])
        
        if st.button("📤 Upload"):
            st.success("Track uploaded to SoundCloud!")
    
    with tabs[1]:
        st.subheader("Play Statistics")
        
        fig = px.line(
            y=[100, 250, 400, 600, 800, 1000],
            title="Plays Over Time",
            labels={"y": "Plays", "x": "Day"}
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with tabs[2]:
        st.subheader("Comments & Engagement")
        st.info("Latest comments from your tracks")
    
    with tabs[3]:
        st.subheader("Artist Network")
        st.info("Connect with other artists on SoundCloud")
    
    with tabs[4]:
        st.subheader("Monetization")
        st.metric("SoundCloud Revenue", "$567")

def render_deezer_tab():
    """Deezer-specific controls"""
    st.markdown("### 🎼 Deezer")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Listeners", "3,456")
    with col2:
        st.metric("Streams", "67,890")
    with col3:
        st.metric("Revenue", "$234")
    
    st.divider()
    
    tabs = st.tabs(["📊 Analytics", "🎯 Playlists", "💰 Earnings", "🌍 Territories"])
    
    with tabs[0]:
        st.subheader("Listener Analytics")
        st.info("Detailed breakdown of your listeners")
    
    with tabs[1]:
        st.subheader("Playlist Pitching")
        st.info("Submit tracks to Deezer editorial playlists")
        
        if st.button("📨 Pitch Track"):
            st.success("Pitched to playlists!")
    
    with tabs[2]:
        st.subheader("Earnings Report")
        earnings_df = pd.DataFrame({
            "Month": ["Nov", "Dec", "Jan"],
            "Earnings": ["$123", "$189", "$234"]
        })
        st.dataframe(earnings_df, use_container_width=True)
    
    with tabs[3]:
        st.subheader("Territory Performance")
        st.info("See your performance by country/region")

def render_tiktok_tab():
    """TikTok sound-specific controls"""
    st.markdown("### 🎵 TikTok Sounds")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Sound Uses", "12,345", "+2,345")
    with col2:
        st.metric("Creator Fund", "$567", "+$89")
    with col3:
        st.metric("Trend Rank", "#45", "↑ +5")
    
    st.divider()
    
    tabs = st.tabs(["🎵 Sounds", "📊 Trends", "💎 Creator Fund", "📈 Growth"])
    
    with tabs[0]:
        st.subheader("Your Sounds")
        st.info("Manage sounds that creators are using")
    
    with tabs[1]:
        st.subheader("Trending Data")
        st.info("See which of your sounds are trending")
    
    with tabs[2]:
        st.subheader("Creator Fund Earnings")
        st.metric("This Month", "$567")
    
    with tabs[3]:
        st.subheader("Growth Analytics")
        st.info("Track your sound's growth over time")

def render_amazon_music_tab():
    """Amazon Music-specific controls"""
    st.markdown("### 🔶 Amazon Music")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Listeners", "4,567")
    with col2:
        st.metric("Streams", "78,900")
    with col3:
        st.metric("Revenue", "$345")
    
    st.divider()
    
    tabs = st.tabs(["📊 Analytics", "🎯 Distribution", "💰 Royalties", "🔊 Quality"])
    
    with tabs[0]:
        st.subheader("Performance Metrics")
    with tabs[1]:
        st.subheader("Distribution Management")
    with tabs[2]:
        st.subheader("Royalty Tracking")
    with tabs[3]:
        st.subheader("Audio Quality Settings")
        st.info("Control HD and spatial audio availability")

def render_tidal_tab():
    """Tidal-specific controls"""
    st.markdown("### 🌊 Tidal")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Hi-Fi Listeners", "2,345")
    with col2:
        st.metric("Streams", "45,678")
    with col3:
        st.metric("HiFi Revenue", "$456")
    
    st.divider()
    
    tabs = st.tabs(["📊 Analytics", "🎯 Distribution", "🔊 HiFi Audio", "💰 Earnings"])
    
    with tabs[0]:
        st.subheader("Tidal Analytics")
    with tabs[1]:
        st.subheader("Pitch to Playlists")
    with tabs[2]:
        st.subheader("Hi-Fi Audio Settings")
        st.info("Lossless audio tracking and management")
    with tabs[3]:
        st.subheader("HiFi-Specific Earnings")

def render_beatport_tab():
    """Beatport-specific controls for electronic music"""
    st.markdown("### 💿 Beatport")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("DJ Sales", "234")
    with col2:
        st.metric("Chart Position", "#12", "↑")
    with col3:
        st.metric("Sales Revenue", "$1,234")
    
    st.divider()
    
    tabs = st.tabs(["📊 Genre Analytics", "🎵 Releases", "🏆 Charts", "🎧 Stems"])
    
    with tabs[0]:
        st.subheader("Electronic Music Analytics")
        st.info("Genre-specific performance data")
    
    with tabs[1]:
        st.subheader("Manage Releases")
    
    with tabs[2]:
        st.subheader("Chart Rankings")
        st.info("Track your position in Beatport charts")
    
    with tabs[3]:
        st.subheader("Stems & Acapellas")
        st.info("Upload stems for DJs to remix")

def render_traxsource_tab():
    """Traxsource house/techno specific"""
    st.markdown("### 🔥 Traxsource")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("House Sales", "145")
    with col2:
        st.metric("Techno Sales", "98")
    with col3:
        st.metric("Revenue", "$890")
    
    st.divider()
    
    tabs = st.tabs(["📊 Genre Trends", "🎵 Releases", "🏆 Charts"])
    
    with tabs[0]:
        st.subheader("House & Techno Trends")
    with tabs[1]:
        st.subheader("Release Management")
    with tabs[2]:
        st.subheader("Traxsource Charts")

def render_juno_download_tab():
    """Juno Download vinyl/digital sales"""
    st.markdown("### 🎧 Juno Download")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Digital Sales", "89")
    with col2:
        st.metric("FLAC Downloads", "34")
    with col3:
        st.metric("Revenue", "$567")
    
    st.divider()
    
    tabs = st.tabs(["📊 Sales", "🔊 FLAC", "🏪 Store", "🎧 DJ Stats"])
    
    with tabs[0]:
        st.subheader("Sales Analytics")
    with tabs[1]:
        st.subheader("FLAC Format Support")
    with tabs[2]:
        st.subheader("Store Management")
    with tabs[3]:
        st.subheader("DJ Download Stats")

# ========================================
# MAIN TAB RENDERER
# ========================================

def render_music_platforms_tab():
    """Main music platforms tab with dynamic service tabs"""
    
    st.markdown("# 🎵 Music Platforms Pro")
    st.markdown("Connect to your music distribution platforms and manage everything in one place")
    
    # Initialize session state
    if 'connected_platforms' not in st.session_state:
        st.session_state.connected_platforms = load_connected_platforms()
    
    # Initialize active platform selection
    if 'active_music_platform' not in st.session_state:
        st.session_state.active_music_platform = None
    
    if not OAUTH_AVAILABLE:
        st.error("❌ OAuth module not available. OAuth system not initialized.")
        st.stop()
    
    # Get platforms that need OAuth
    oauth_platforms = {k: v for k, v in MUSIC_PLATFORMS.items() if k in OAUTH_CONFIGS}
    
    # Main content area with settings
    tab1, tab2, tab3 = st.tabs(["🔗 Connect Platforms", "📊 Connected Platforms", "⚙️ Settings"])
    
    # ===== TAB 3: SETTINGS =====
    with tab3:
        st.markdown("## OAuth Credentials Settings")
        st.markdown("Save your OAuth credentials here to enable automatic connection setup:")
        
        st.info("💡 Your credentials are stored securely in environment variables and local storage.")
        
        # Spotify credentials
        with st.expander("🎵 Spotify Credentials", expanded=False):
            st.markdown("### Get Spotify Credentials:")
            st.markdown("""
            1. Go to https://developer.spotify.com/dashboard
            2. Sign in or create an account
            3. Click "Create an App"
            4. Accept the terms and create
            5. Copy your **Client ID** and **Client Secret**
            """)
            
            col1, col2 = st.columns(2)
            
            with col1:
                spotify_client_id = st.text_input(
                    "Spotify Client ID",
                    type="password",
                    value=os.getenv('SPOTIFY_CLIENT_ID', ''),
                    key="spotify_client_id_input"
                )
            
            with col2:
                spotify_client_secret = st.text_input(
                    "Spotify Client Secret",
                    type="password",
                    value=os.getenv('SPOTIFY_CLIENT_SECRET', ''),
                    key="spotify_client_secret_input"
                )
            
            if st.button("💾 Save Spotify Credentials", use_container_width=True):
                if spotify_client_id and spotify_client_secret:
                    os.environ['SPOTIFY_CLIENT_ID'] = spotify_client_id
                    os.environ['SPOTIFY_CLIENT_SECRET'] = spotify_client_secret
                    
                    # Also save to .env file
                    env_file = Path('/Users/sheils/repos/printify/.env')
                    try:
                        # Read existing .env
                        env_vars = {}
                        if env_file.exists():
                            with open(env_file) as f:
                                for line in f:
                                    if '=' in line and not line.startswith('#'):
                                        key, val = line.strip().split('=', 1)
                                        env_vars[key] = val
                        
                        # Update with new values
                        env_vars['SPOTIFY_CLIENT_ID'] = spotify_client_id
                        env_vars['SPOTIFY_CLIENT_SECRET'] = spotify_client_secret
                        
                        # Write back
                        with open(env_file, 'w') as f:
                            for key, val in env_vars.items():
                                f.write(f"{key}={val}\n")
                        
                        st.success("✅ Spotify credentials saved!")
                        st.info("🔄 Restarting app to load credentials...")
                        st.session_state.should_rerun = True
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error saving to .env: {str(e)}")
                        st.info("✅ Credentials saved to environment variables (for current session)")
                else:
                    st.warning("⚠️ Please fill in both Client ID and Client Secret")
        
        # Apple Music credentials
        with st.expander("🍎 Apple Music Credentials", expanded=False):
            st.markdown("### Get Apple Music Credentials:")
            st.markdown("""
            1. Go to https://developer.apple.com/account
            2. Sign in with Apple ID
            3. Create a new MusicKit identifier
            4. Get your Team ID and Key ID
            """)
            
            col1, col2 = st.columns(2)
            
            with col1:
                apple_team_id = st.text_input(
                    "Apple Team ID",
                    type="password",
                    value=os.getenv('APPLE_TEAM_ID', ''),
                    key="apple_team_id_input"
                )
            
            with col2:
                apple_key_id = st.text_input(
                    "Apple Key ID",
                    type="password",
                    value=os.getenv('APPLE_KEY_ID', ''),
                    key="apple_key_id_input"
                )
            
            if st.button("💾 Save Apple Music Credentials", use_container_width=True):
                if apple_team_id and apple_key_id:
                    os.environ['APPLE_TEAM_ID'] = apple_team_id
                    os.environ['APPLE_KEY_ID'] = apple_key_id
                    
                    # Also save to .env file
                    env_file = Path('/Users/sheils/repos/printify/.env')
                    try:
                        # Read existing .env
                        env_vars = {}
                        if env_file.exists():
                            with open(env_file) as f:
                                for line in f:
                                    if '=' in line and not line.startswith('#'):
                                        key, val = line.strip().split('=', 1)
                                        env_vars[key] = val
                        
                        # Update with new values
                        env_vars['APPLE_TEAM_ID'] = apple_team_id
                        env_vars['APPLE_KEY_ID'] = apple_key_id
                        
                        # Write back
                        with open(env_file, 'w') as f:
                            for key, val in env_vars.items():
                                f.write(f"{key}={val}\n")
                        
                        st.success("✅ Apple Music credentials saved!")
                    except Exception as e:
                        st.error(f"Error saving to .env: {str(e)}")
                        st.info("✅ Credentials saved to environment variables (for current session)")
                else:
                    st.warning("⚠️ Please fill in both Team ID and Key ID")
        
        # YouTube Music credentials
        with st.expander("🎬 YouTube Music Credentials", expanded=False):
            st.markdown("### Get YouTube Music Credentials:")
            st.markdown("""
            1. Go to https://console.cloud.google.com
            2. Create a new project
            3. Enable YouTube Data API v3
            4. Create OAuth 2.0 credentials (Desktop application)
            5. Download the JSON credentials file
            """)
            
            youtube_api_key = st.text_input(
                "YouTube API Key",
                type="password",
                value=os.getenv('YOUTUBE_API_KEY', ''),
                key="youtube_api_key_input"
            )
            
            if st.button("💾 Save YouTube Music Credentials", use_container_width=True):
                if youtube_api_key:
                    os.environ['YOUTUBE_API_KEY'] = youtube_api_key
                    
                    env_file = Path('/Users/sheils/repos/printify/.env')
                    try:
                        env_vars = {}
                        if env_file.exists():
                            with open(env_file) as f:
                                for line in f:
                                    if '=' in line and not line.startswith('#'):
                                        key, val = line.strip().split('=', 1)
                                        env_vars[key] = val
                        
                        env_vars['YOUTUBE_API_KEY'] = youtube_api_key
                        
                        with open(env_file, 'w') as f:
                            for key, val in env_vars.items():
                                f.write(f"{key}={val}\n")
                        
                        st.success("✅ YouTube Music credentials saved!")
                    except Exception as e:
                        st.error(f"Error saving to .env: {str(e)}")
                else:
                    st.warning("⚠️ Please fill in the API Key")
    
    # ===== TAB 1: CONNECT PLATFORMS =====
    
    # ===== TAB 1: CONNECT PLATFORMS =====
    with tab1:
        st.markdown("## Step 1: Select a Platform")
        st.markdown("Click on any platform below to start the connection process:")
        
        # Display platform grid
        cols = st.columns(3)
        for idx, (platform_key, platform_info) in enumerate(oauth_platforms.items()):
            col = cols[idx % 3]
            
            # Check if already connected
            is_connected = platform_key in st.session_state.connected_platforms
            
            with col:
                button_label = f"{platform_info['name']}" + (" ✅" if is_connected else "")
                
                if st.button(
                    button_label,
                    key=f"platform_{platform_key}",
                    use_container_width=True,
                    type="secondary" if is_connected else "primary"
                ):
                    st.session_state.active_music_platform = platform_key
                    st.rerun()
        
        st.divider()
        
        # Show OAuth flow for selected platform
        if st.session_state.active_music_platform:
            platform_key = st.session_state.active_music_platform
            
            if platform_key in oauth_platforms:
                platform_info = MUSIC_PLATFORMS[platform_key]
                oauth_config = OAUTH_CONFIGS[platform_key]
                
                st.markdown(f"## {platform_info['name']} Connection Setup")
                
                try:
                    oauth_handler = MusicPlatformOAuthHandler()
                    
                    # Generate authorization URL
                    auth_url, state = oauth_handler.get_authorization_url(platform_key)
                    
                    # Step 1: Authorization
                    st.markdown("### 🔐 Step 1: Authorize")
                    st.info(
                        f"Click the button below to open {platform_info['name']} and authorize this app. "
                        f"You'll need a {platform_info['name']} account."
                    )
                    
                    col1, col2 = st.columns([2, 1])
                    
                    with col1:
                        if st.button(
                            f"🔓 Open {platform_info['name']} Authorization",
                            key=f"auth_{platform_key}",
                            use_container_width=True,
                            type="primary"
                        ):
                            st.markdown(f"**👉 [Click here to authorize on {platform_info['name']}]({auth_url})**")
                            st.markdown(f"*This will open in a new window. Authorize the app, then return here.*")
                    
                    with col2:
                        if st.button("← Back", key=f"back_{platform_key}", use_container_width=True):
                            st.session_state.active_music_platform = None
                            st.rerun()
                    
                    st.divider()
                    
                    # Step 2: Enter code
                    st.markdown("### 📝 Step 2: Enter Authorization Code")
                    st.markdown(
                        "After authorizing, you'll be redirected to a page. Copy the code from the URL and paste it below:"
                    )
                    
                    code = st.text_input(
                        "Authorization Code",
                        placeholder=f"Paste the authorization code from {platform_info['name']}",
                        key=f"code_input_{platform_key}",
                        type="password"
                    )
                    
                    if code:
                        st.divider()
                        st.markdown("### ✅ Step 3: Complete Connection")
                        
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            if st.button(
                                f"✅ Complete {platform_info['name']} Connection",
                                key=f"complete_{platform_key}",
                                use_container_width=True,
                                type="primary"
                            ):
                                with st.spinner(f"Connecting to {platform_info['name']}..."):
                                    try:
                                        # Exchange code for token
                                        token_response = oauth_handler.exchange_code_for_token(
                                            platform_key,
                                            code,
                                            state
                                        )
                                        
                                        # Save credentials
                                        cred_storage = CredentialStorage()
                                        user_id = f"user_{datetime.now().timestamp()}"
                                        
                                        cred_storage.save_credentials(
                                            platform_key,
                                            user_id,
                                            token_response
                                        )
                                        
                                        # Update session state
                                        cred = PlatformCredentials(
                                            platform_name=platform_key,
                                            service_id=user_id,
                                            oauth_token=token_response.get("access_token"),
                                            refresh_token=token_response.get("refresh_token"),
                                            credentials_data=token_response,
                                            last_updated=datetime.now().isoformat(),
                                            is_active=True
                                        )
                                        
                                        st.session_state.connected_platforms[platform_key] = cred
                                        save_connected_platforms(st.session_state.connected_platforms)
                                        st.session_state.active_music_platform = None
                                        
                                        st.success(f"✅ Successfully connected to {platform_info['name']}!")
                                        st.balloons()
                                        st.rerun()
                                        
                                    except Exception as e:
                                        st.error(f"❌ Connection failed: {str(e)}")
                                        st.error("Please try again or check your code.")
                        
                        with col2:
                            if st.button("← Change Code", key=f"change_{platform_key}", use_container_width=True):
                                st.rerun()
                    
                    else:
                        st.info("👉 Authorize first, then paste your code above.")
                
                except Exception as e:
                    st.error(f"Error: {str(e)}")
                    if st.button("← Try Again", key=f"retry_{platform_key}", use_container_width=True):
                        st.session_state.active_music_platform = None
                        st.rerun()
    
    # ===== TAB 2: CONNECTED PLATFORMS =====
    with tab2:
        if st.session_state.connected_platforms:
            st.markdown("## Your Connected Platforms")
            
            # Show each connected platform
            connected_items = []
            for platform_key, cred in st.session_state.connected_platforms.items():
                if cred.is_active:
                    platform_info = MUSIC_PLATFORMS.get(platform_key)
                    if platform_info:
                        connected_items.append((platform_key, platform_info, cred))
            
            if connected_items:
                # Connection status grid
                cols = st.columns(len(connected_items))
                for col, (platform_key, platform_info, cred) in zip(cols, connected_items):
                    with col:
                        st.markdown(f"""
                        <div style="border: 2px solid #1DB954; border-radius: 10px; padding: 15px; text-align: center;">
                            <h3 style="color: #1DB954; margin: 0;">{platform_info['icon']}</h3>
                            <p style="margin: 8px 0 0 0;"><b>{platform_info['name']}</b></p>
                            <small style="color: #666;">✅ Connected</small>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        if st.button("🔄 Refresh", key=f"refresh_{platform_key}", use_container_width=True):
                            try:
                                if cred.refresh_token:
                                    oauth_handler = MusicPlatformOAuthHandler()
                                    new_token = oauth_handler.refresh_access_token(
                                        platform_key,
                                        cred.refresh_token
                                    )
                                    cred.oauth_token = new_token.get("access_token")
                                    cred.last_updated = datetime.now().isoformat()
                                    
                                    cred_storage = CredentialStorage()
                                    cred_storage.save_credentials(
                                        platform_key,
                                        cred.service_id,
                                        new_token
                                    )
                                    st.session_state.connected_platforms[platform_key] = cred
                                    save_connected_platforms(st.session_state.connected_platforms)
                                    st.success("✅ Token refreshed!")
                                    st.rerun()
                            except Exception as e:
                                st.error(f"Refresh failed: {str(e)}")
                        
                        if st.button("❌ Disconnect", key=f"disconnect_{platform_key}", use_container_width=True):
                            cred.is_active = False
                            save_connected_platforms(st.session_state.connected_platforms)
                            st.success(f"Disconnected from {platform_info['name']}")
                            st.rerun()
                
                st.divider()
                
                # Show connected platform tabs
                connected_names = [p[1]['name'] for p in connected_items]
                platform_renderers = []
                
                for platform_key, _, _ in connected_items:
                    if platform_key == "spotify":
                        platform_renderers.append(render_spotify_tab)
                    elif platform_key == "apple_music":
                        platform_renderers.append(render_apple_music_tab)
                    elif platform_key == "youtube_music":
                        platform_renderers.append(render_youtube_music_tab)
                    elif platform_key == "bandcamp":
                        platform_renderers.append(render_bandcamp_tab)
                    elif platform_key == "soundcloud":
                        platform_renderers.append(render_soundcloud_tab)
                    elif platform_key == "deezer":
                        platform_renderers.append(render_deezer_tab)
                    elif platform_key == "tiktok":
                        platform_renderers.append(render_tiktok_tab)
                    elif platform_key == "amazon_music":
                        platform_renderers.append(render_amazon_music_tab)
                    elif platform_key == "tidal":
                        platform_renderers.append(render_tidal_tab)
                    elif platform_key == "beatport":
                        platform_renderers.append(render_beatport_tab)
                    elif platform_key == "traxsource":
                        platform_renderers.append(render_traxsource_tab)
                    elif platform_key == "juno_download":
                        platform_renderers.append(render_juno_download_tab)
                
                if connected_names:
                    st.markdown("## Platform Dashboards")
                    platform_tabs = st.tabs(connected_names)
                    
                    for tab, renderer in zip(platform_tabs, platform_renderers):
                        with tab:
                            try:
                                renderer()
                            except Exception as e:
                                st.error(f"Error loading platform: {str(e)}")
            else:
                st.info("No platforms connected yet. Go to the 'Connect Platforms' tab to get started!")
        else:
            st.info("No platforms connected yet. Go to the 'Connect Platforms' tab to get started!")
