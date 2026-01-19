"""
Chat History Management System
Handles conversation persistence, loading, searching, and management.
"""

from app.tabs.abp_imports_common import (
    st, os, json, logging, uuid, Path, Dict, List, Any, Optional,
    datetime, setup_logger
)

logger = setup_logger(__name__)


class ChatHistoryManager:
    """
    Manages chat conversation history with save/load capabilities.
    Stores conversations as JSON files in the file library for easy access.
    """
    
    CONVERSATIONS_DIR = "file_library/conversations"
    
    def __init__(self):
        """Initialize the chat history manager."""
        self.conversations_path = Path(self.CONVERSATIONS_DIR)
        self._ensure_directory()
    
    def _ensure_directory(self):
        """Ensure the conversations directory exists."""
        self.conversations_path.mkdir(parents=True, exist_ok=True)
    
    def generate_conversation_id(self) -> str:
        """Generate a unique conversation ID."""
        return f"chat_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
    
    def get_conversation_title(self, messages: List[Dict]) -> str:
        """Generate a title from the first user message or use default."""
        for msg in messages:
            if msg.get('role') == 'user':
                content = msg.get('content', '')
                # Truncate and clean for title
                title = content[:50].replace('\n', ' ').strip()
                if len(content) > 50:
                    title += "..."
                return title
        return f"Conversation {datetime.now().strftime('%b %d, %H:%M')}"
    
    def save_conversation(self, messages: List[Dict], conversation_id: Optional[str] = None, 
                          title: Optional[str] = None) -> Dict[str, Any]:
        """
        Save a conversation to the file library.
        
        Args:
            messages: List of chat messages
            conversation_id: Optional existing ID to update
            title: Optional custom title
            
        Returns:
            Dict with success status and conversation metadata
        """
        try:
            self._ensure_directory()
            
            if not messages:
                return {"success": False, "error": "No messages to save"}
            
            # Generate or use existing ID
            conv_id = conversation_id or self.generate_conversation_id()
            
            # Generate title if not provided
            conv_title = title or self.get_conversation_title(messages)
            
            # Create conversation metadata
            conversation = {
                "id": conv_id,
                "title": conv_title,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "message_count": len(messages),
                "messages": messages,
                "summary": self._generate_summary(messages)
            }
            
            # Save to file
            file_path = self.conversations_path / f"{conv_id}.json"
            with open(file_path, 'w') as f:
                json.dump(conversation, f, indent=2, default=str)
            
            return {
                "success": True,
                "id": conv_id,
                "title": conv_title,
                "file_path": str(file_path)
            }
            
        except Exception as e:
            logging.error(f"Failed to save conversation: {e}")
            return {"success": False, "error": str(e)}
    
    def _generate_summary(self, messages: List[Dict]) -> str:
        """Generate a brief summary of the conversation."""
        user_msgs = [m['content'][:100] for m in messages if m.get('role') == 'user'][:3]
        return " | ".join(user_msgs) if user_msgs else "Empty conversation"
    
    def load_conversation(self, conversation_id: str) -> Dict[str, Any]:
        """
        Load a conversation from the file library.
        
        Args:
            conversation_id: The conversation ID to load
            
        Returns:
            Dict with conversation data or error
        """
        try:
            file_path = self.conversations_path / f"{conversation_id}.json"
            
            if not file_path.exists():
                return {"success": False, "error": "Conversation not found"}
            
            with open(file_path, 'r') as f:
                conversation = json.load(f)
            
            return {
                "success": True,
                "conversation": conversation
            }
            
        except Exception as e:
            logging.error(f"Failed to load conversation: {e}")
            return {"success": False, "error": str(e)}
    
    def list_conversations(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        List all saved conversations, sorted by most recent.
        
        Args:
            limit: Maximum number of conversations to return
            
        Returns:
            List of conversation metadata
        """
        try:
            self._ensure_directory()
            conversations = []
            
            for file_path in self.conversations_path.glob("*.json"):
                try:
                    with open(file_path, 'r') as f:
                        data = json.load(f)
                        conversations.append({
                            "id": data.get("id", file_path.stem),
                            "title": data.get("title", "Untitled"),
                            "created_at": data.get("created_at"),
                            "updated_at": data.get("updated_at"),
                            "message_count": data.get("message_count", 0),
                            "summary": data.get("summary", "")[:100]
                        })
                except:
                    continue
            
            # Sort by updated_at descending
            conversations.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
            
            return conversations[:limit]
            
        except Exception as e:
            logging.error(f"Failed to list conversations: {e}")
            return []
    
    def delete_conversation(self, conversation_id: str) -> Dict[str, Any]:
        """
        Delete a conversation.
        
        Args:
            conversation_id: The conversation ID to delete
            
        Returns:
            Dict with success status
        """
        try:
            file_path = self.conversations_path / f"{conversation_id}.json"
            
            if file_path.exists():
                file_path.unlink()
                return {"success": True}
            
            return {"success": False, "error": "Conversation not found"}
            
        except Exception as e:
            logging.error(f"Failed to delete conversation: {e}")
            return {"success": False, "error": str(e)}
    
    def search_conversations(self, query: str) -> List[Dict[str, Any]]:
        """
        Search conversations by title or content.
        
        Args:
            query: Search query
            
        Returns:
            List of matching conversations
        """
        try:
            query_lower = query.lower()
            results = []
            
            for file_path in self.conversations_path.glob("*.json"):
                try:
                    with open(file_path, 'r') as f:
                        data = json.load(f)
                        
                        # Search in title and messages
                        title = data.get("title", "").lower()
                        messages_text = " ".join([
                            m.get("content", "").lower() 
                            for m in data.get("messages", [])
                        ])
                        
                        if query_lower in title or query_lower in messages_text:
                            results.append({
                                "id": data.get("id"),
                                "title": data.get("title"),
                                "created_at": data.get("created_at"),
                                "message_count": data.get("message_count", 0),
                                "summary": data.get("summary", "")[:100]
                            })
                except:
                    continue
            
            return results
            
        except Exception as e:
            logging.error(f"Failed to search conversations: {e}")
            return []


# Singleton instance
_chat_history_manager = None

def get_chat_history_manager() -> ChatHistoryManager:
    """Get the singleton chat history manager instance."""
    global _chat_history_manager
    if _chat_history_manager is None:
        _chat_history_manager = ChatHistoryManager()
    return _chat_history_manager


def render_chat_history_sidebar(key_suffix: str = "main"):
    """
    Render the chat history management UI in sidebar or expander.
    Shows saved conversations list with search.
    
    Args:
        key_suffix: Unique key suffix for widgets
    """
    manager = get_chat_history_manager()
    
    # Search conversations
    search_query = st.text_input(
        "🔍 Search chats",
        placeholder="Search saved conversations...",
        key=f"search_chats_{key_suffix}",
        label_visibility="collapsed"
    )
    
    # Load conversations
    if search_query:
        conversations = manager.search_conversations(search_query)
    else:
        conversations = manager.list_conversations(limit=20)
    
    # Display conversation list
    if conversations:
        st.caption(f"📚 {len(conversations)} saved conversation(s)")
        
        for conv in conversations:
            with st.container():
                col1, col2 = st.columns([5, 1])
                
                with col1:
                    # Format date
                    try:
                        created = datetime.fromisoformat(conv.get('created_at', ''))
                        date_str = created.strftime("%b %d, %H:%M")
                    except:
                        date_str = "Unknown"
                    
                    title = conv.get('title', 'Untitled')[:35]
                    if len(conv.get('title', '')) > 35:
                        title += "..."
                    
                    if st.button(
                        f"📝 {title}",
                        key=f"load_{conv['id']}_{key_suffix}",
                        help=f"{date_str} • {conv.get('message_count', 0)} messages",
                        use_container_width=True
                    ):
                        # Save current first
                        if st.session_state.get('chat_history', []):
                            current_id = st.session_state.get('current_conversation_id')
                            if current_id != conv['id']:
                                manager.save_conversation(
                                    st.session_state.chat_history,
                                    conversation_id=current_id
                                )
                        
                        # Load selected
                        result = manager.load_conversation(conv['id'])
                        if result.get("success"):
                            st.session_state.chat_history = result["conversation"]["messages"]
                            st.session_state.current_conversation_id = conv['id']
                            st.rerun()
                        else:
                            st.error(f"Failed to load: {result.get('error')}")
                
                with col2:
                    if st.button("🗑", key=f"del_{conv['id']}_{key_suffix}", help="Delete"):
                        manager.delete_conversation(conv['id'])
                        st.rerun()
    else:
        st.info("💬 No saved conversations yet")
        st.caption("Start chatting and save to build your history!")


__all__ = [
    'ChatHistoryManager',
    'get_chat_history_manager',
    'render_chat_history_sidebar'
]
