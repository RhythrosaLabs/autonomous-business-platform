"""
Smart Dashboard Widget - Intelligent KPI Display and Recommendations
=====================================================================

Auto-updates with real-time stats, insights, and actionable recommendations
"""

import streamlit as st
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger(__name__)


class SmartDashboard:
    """Intelligent dashboard with contextual metrics and insights"""
    
    @staticmethod
    def get_dashboard_metrics() -> Dict[str, Any]:
        """Collect all relevant metrics for dashboard"""
        
        campaigns = st.session_state.get('campaign_history', [])
        products = st.session_state.get('generated_products', [])
        content = st.session_state.get('generated_content', [])
        videos = st.session_state.get('generated_videos', [])
        shortcuts = st.session_state.get('magic_shortcuts', [])
        scheduled = st.session_state.get('scheduled_items', [])
        conversations = st.session_state.get('chat_history', [])
        
        # Calculate time-based metrics
        today = datetime.now()
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)
        
        # Metrics
        return {
            # Volume metrics
            'total_campaigns': len(campaigns),
            'total_products': len(products),
            'total_content': len(content),
            'total_videos': len(videos),
            'total_shortcuts': len(shortcuts),
            
            # This week/month
            'campaigns_this_week': SmartDashboard._count_since(campaigns, week_ago),
            'products_this_week': SmartDashboard._count_since(products, week_ago),
            'content_this_month': SmartDashboard._count_since(content, month_ago),
            
            # Engagement metrics (if available)
            'avg_engagement': SmartDashboard._calculate_avg_engagement(campaigns),
            'most_shared_platform': SmartDashboard._get_most_used_platform(scheduled),
            
            # Quality metrics
            'completed_campaigns': len([c for c in campaigns if c.get('status') == 'completed']),
            'scheduled_posts': len([s for s in scheduled if s.get('status') == 'scheduled']),
            'published_content': len([p for p in content if p.get('published', False)]),
            
            # Activity
            'chat_messages': len(conversations),
            'total_shortcuts_used': sum(s.get('run_count', 0) for s in shortcuts),
        }
    
    @staticmethod
    def _count_since(items: List[Dict], since_date: datetime) -> int:
        """Count items created/updated since date"""
        count = 0
        for item in items:
            date_val = item.get('date') or item.get('created_at') or item.get('timestamp')
            if not date_val: continue
            try:
                item_date = datetime.fromisoformat(date_val) if isinstance(date_val, str) else date_val
                if item_date >= since_date: count += 1
            except: pass
        return count
    
    @staticmethod
    def _calculate_avg_engagement(campaigns: List[Dict]) -> str:
        """Calculate average engagement across campaigns"""
        if not campaigns:
            return "N/A"
        
        engagements = [c.get('engagement', 0) for c in campaigns if c.get('engagement')]
        if engagements:
            avg = sum(engagements) / len(engagements)
            return f"{avg:.0f}"
        return "N/A"
    
    @staticmethod
    def _get_most_used_platform(scheduled: List[Dict]) -> str:
        """Get most frequently scheduled platform"""
        platforms = {}
        
        for item in scheduled:
            plat_list = item.get('platforms', [])
            for plat in plat_list:
                platforms[plat] = platforms.get(plat, 0) + 1
        
        if platforms:
            return max(platforms.items(), key=lambda x: x[1])[0]
        return "None"
    
    @staticmethod
    def render_smart_dashboard():
        """Render the smart dashboard widget"""
        
        st.markdown("### 📊 Smart Dashboard")
        
        metrics = SmartDashboard.get_dashboard_metrics()
        
        # Key metrics - 4 columns
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "📦 Total Campaigns",
                metrics['total_campaigns'],
                f"↑ {metrics['campaigns_this_week']} this week",
                delta_color="off"
            )
        
        with col2:
            st.metric(
                "🎨 Products",
                metrics['total_products'],
                f"↑ {metrics['products_this_week']} this week",
                delta_color="off"
            )
        
        with col3:
            st.metric(
                "📝 Content",
                metrics['total_content'],
                f"↑ {metrics['content_this_month']} this month",
                delta_color="off"
            )
        
        with col4:
            st.metric(
                "🎬 Videos",
                metrics['total_videos'],
                f"📺 {metrics['scheduled_posts']} scheduled",
                delta_color="off"
            )
        
        st.markdown("---")
        
        # Secondary metrics - 3 columns
        col_a, col_b, col_c = st.columns(3)
        
        with col_a:
            st.metric(
                "🎯 Avg Engagement",
                metrics['avg_engagement'],
                help="Average engagement across campaigns"
            )
        
        with col_b:
            st.metric(
                "📱 Top Platform",
                metrics['most_shared_platform'],
                help="Most frequently scheduled platform"
            )
        
        with col_c:
            st.metric(
                "✅ Published",
                metrics['published_content'],
                help="Content pieces published"
            )
        
        st.markdown("---")
        
        # Productivity summary
        st.markdown("#### 🚀 Productivity Summary")
        
        summary_col1, summary_col2 = st.columns(2)
        
        with summary_col1:
            st.markdown(f"""
            **This Week:**
            - 📦 {metrics['campaigns_this_week']} campaigns created
            - 🎨 {metrics['products_this_week']} product designs
            - 📅 {metrics['scheduled_posts']} posts scheduled
            """)
        
        with summary_col2:
            total_generated = metrics['total_campaigns'] + metrics['total_products'] + metrics['total_content']
            st.markdown(f"""
            **All Time:**
            - 🎯 {total_generated} total assets created
            - 💬 {metrics['chat_messages']} chat messages
            - ⚡ {metrics['total_shortcuts_used']} shortcut uses
            """)
        
        st.markdown("---")
        
        # Insights & recommendations
        st.markdown("#### 💡 AI Insights & Recommendations")
        
        insights = SmartDashboard._generate_insights(metrics)
        
        if not insights:
            st.info("🎉 Everything looks great! Keep creating content and we'll provide insights as your business grows.")
        else:
            # Create a grid layout for insights
            cols_per_row = 2
            for i in range(0, len(insights), cols_per_row):
                cols = st.columns(cols_per_row)
                for j, col in enumerate(cols):
                    if i + j < len(insights):
                        insight = insights[i + j]
                        with col:
                            # Color based on priority
                            if insight.get('priority') == 'high':
                                border_color = "#FF6B6B"
                                bg_color = "#FFF5F5"
                            elif insight.get('priority') == 'medium':
                                border_color = "#FFB84D"
                                bg_color = "#FFF9F0"
                            else:
                                border_color = "#4ECDC4"
                                bg_color = "#F0FFFE"
                            
                            # Create card
                            st.markdown(f"""
                            <div style="
                                padding: 20px;
                                border-radius: 10px;
                                border-left: 4px solid {border_color};
                                background-color: {bg_color};
                                margin-bottom: 15px;
                                min-height: 180px;
                            ">
                                <h4 style="margin: 0 0 10px 0;">{insight['icon']} {insight['title']}</h4>
                                <p style="margin: 0 0 15px 0; color: #666;">{insight['description']}</p>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            if 'action' in insight:
                                if st.button(f"🔧 {insight['action']['label']}", key=f"insight_{insight['title']}", use_container_width=True):
                                    st.session_state['insight_action'] = insight['action']['id']
                                    st.rerun()
    
    @staticmethod
    def _generate_insights(metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate contextual insights based on metrics"""
        
        insights = []
        
        # Insight: Lots of products but no campaigns
        if metrics['total_products'] > 5 and metrics['total_campaigns'] == 0:
            insights.append({
                'icon': '🎯',
                'title': 'Launch Your First Campaign',
                'description': f"You've created {metrics['total_products']} products. Create a campaign to market them!",
                'priority': 'high',
                'action': {'id': 'create_campaign', 'label': 'Create Campaign'}
            })
        
        # Insight: Good campaign velocity
        if metrics['campaigns_this_week'] >= 2:
            insights.append({
                'icon': '🔥',
                'title': 'Great Campaign Velocity!',
                'description': f"You've created {metrics['campaigns_this_week']} campaigns this week. Keep up the momentum!",
                'priority': 'low'
            })
        
        # Insight: No videos yet
        if metrics['total_videos'] == 0 and metrics['total_campaigns'] > 0:
            insights.append({
                'icon': '🎬',
                'title': 'Add Video Content',
                'description': "Videos get 80% more engagement. Create your first product video!",
                'priority': 'high',
                'action': {'id': 'create_video', 'label': 'Create Video'}
            })
        
        # Insight: Content not being scheduled
        if metrics['total_content'] > 3 and metrics['scheduled_posts'] == 0:
            insights.append({
                'icon': '📅',
                'title': 'Schedule Your Content',
                'description': f"You have {metrics['total_content']} pieces of content. Schedule them for automatic posting!",
                'priority': 'high',
                'action': {'id': 'schedule_content', 'label': 'Setup Schedule'}
            })
        
        # Insight: Shortcuts not being used
        if metrics['total_shortcuts'] > 0 and metrics['total_shortcuts_used'] == 0:
            insights.append({
                'icon': '⚡',
                'title': 'Use Your Shortcuts',
                'description': f"You have {metrics['total_shortcuts']} shortcuts that can save you time. Try using them!",
                'priority': 'medium'
            })
        
        # Insight: High engagement
        try:
            avg_eng = float(metrics['avg_engagement'])
            if avg_eng > 100:
                insights.append({
                    'icon': '📈',
                    'title': 'Excellent Engagement!',
                    'description': f"Your campaigns are getting {metrics['avg_engagement']} avg engagement. Your content resonates!",
                    'priority': 'low'
                })
        except:
            pass
        
        # Insight: Growing content library
        if metrics['total_content'] > 10:
            insights.append({
                'icon': '📚',
                'title': 'Build Your Content Library',
                'description': f"You have a great library of {metrics['total_content']} content pieces. Organize by theme!",
                'priority': 'low'
            })
        
        return insights


class ActivityFeed:
    """Activity timeline showing recent actions"""
    
    @staticmethod
    def get_recent_activity(limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent activity across all features"""
        
        activity = []
        
        # Get recent campaigns
        campaigns = st.session_state.get('campaign_history', [])
        for campaign in campaigns[-3:]:
            activity.append({
                'timestamp': campaign.get('date', ''),
                'type': 'campaign',
                'icon': '🎯',
                'title': f"Campaign created: {campaign.get('name', 'Untitled')}",
                'detail': campaign.get('description', '')[:80]
            })
        
        # Get recent products
        products = st.session_state.get('generated_products', [])
        for product in products[-3:]:
            activity.append({
                'timestamp': product.get('date', ''),
                'type': 'product',
                'icon': '🎨',
                'title': f"Product designed: {product.get('name', 'Untitled')}",
                'detail': product.get('prompt', '')[:80]
            })
        
        # Get recent shortcuts used
        shortcuts = st.session_state.get('magic_shortcuts', [])
        for shortcut in [s for s in shortcuts if s.get('last_run')]:
            activity.append({
                'timestamp': shortcut.get('last_run', ''),
                'type': 'shortcut',
                'icon': '⚡',
                'title': f"Shortcut used: {shortcut.get('name', 'Untitled')}",
                'detail': f"{shortcut.get('run_count', 0)} total runs"
            })
        
        # Sort by timestamp (newest first)
        activity.sort(key=lambda x: x['timestamp'], reverse=True)
        
        return activity[:limit]
    
    @staticmethod
    def render_activity_feed():
        """Render activity timeline"""
        
        st.markdown("### 📋 Recent Activity")
        
        activity = ActivityFeed.get_recent_activity(8)
        
        if activity:
            for item in activity:
                with st.container():
                    col_icon, col_content = st.columns([0.5, 4])
                    
                    with col_icon:
                        st.markdown(f"<h3>{item['icon']}</h3>", unsafe_allow_html=True)
                    
                    with col_content:
                        st.markdown(f"**{item['title']}**")
                        if item['detail']:
                            st.caption(item['detail'])
                        if item['timestamp']:
                            try:
                                ts = datetime.fromisoformat(item['timestamp'])
                                time_diff = datetime.now() - ts
                                if time_diff.days == 0:
                                    time_str = f"{time_diff.seconds // 3600} hours ago"
                                else:
                                    time_str = f"{time_diff.days} days ago"
                                st.caption(f"⏱️ {time_str}")
                            except:
                                pass
                    
                    st.markdown("---")
        else:
            st.info("📭 No recent activity. Start creating!")


class NotificationCenter:
    """Notification management for important events"""
    
    NOTIFICATION_TYPES = {
        'success': {'icon': '✅', 'color': 'green'},
        'warning': {'icon': '⚠️', 'color': 'yellow'},
        'error': {'icon': '❌', 'color': 'red'},
        'info': {'icon': 'ℹ️', 'color': 'blue'},
        'milestone': {'icon': '🎉', 'color': 'orange'}
    }
    
    @staticmethod
    def add_notification(message: str, notification_type: str = 'info', priority: int = 0):
        """Add notification to queue"""
        
        if 'notifications' not in st.session_state:
            st.session_state.notifications = []
        
        notification = {
            'id': len(st.session_state.notifications),
            'message': message,
            'type': notification_type,
            'priority': priority,
            'timestamp': datetime.now().isoformat(),
            'read': False
        }
        
        st.session_state.notifications.append(notification)
    
    @staticmethod
    def get_unread_notifications(limit: int = 5) -> List[Dict]:
        """Get unread notifications"""
        
        if 'notifications' not in st.session_state:
            return []
        
        unread = [n for n in st.session_state.notifications if not n['read']]
        
        # Sort by priority (high first) then by timestamp (newest first)
        unread.sort(key=lambda x: (-x['priority'], x['timestamp']), reverse=True)
        
        return unread[:limit]
    
    @staticmethod
    def render_notification_bell():
        """Render notification bell in sidebar"""
        
        unread = NotificationCenter.get_unread_notifications()
        
        if unread:
            with st.sidebar:
                st.markdown("---")
                st.markdown("### 🔔 Notifications")
                
                for notification in unread:
                    notif_type = notification.get('type', 'info')
                    notif_icon = NotificationCenter.NOTIFICATION_TYPES.get(notif_type, {}).get('icon', 'ℹ️')
                    
                    with st.container():
                        col1, col2 = st.columns([4, 1])
                        
                        with col1:
                            st.markdown(f"{notif_icon} {notification['message']}")
                        
                        with col2:
                            if st.button("✓", key=f"read_{notification['id']}", help="Mark as read"):
                                notification['read'] = True
                
                st.markdown("---")


# Export public API
__all__ = [
    'SmartDashboard',
    'ActivityFeed',
    'NotificationCenter'
]
