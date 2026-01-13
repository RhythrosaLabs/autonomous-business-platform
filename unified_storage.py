"""
Unified File Storage and Memory Tracking System
Automatically saves all generated content to library and updates Otto's memory
"""
import streamlit as st
from pathlib import Path
from datetime import datetime
import json
import shutil
from typing import Optional, Dict, Any, List
import logging

logger = logging.getLogger(__name__)


class UnifiedStorageManager:
    """Centralized storage manager for all generated content"""
    
    def __init__(self, workspace_root: Optional[Path] = None):
        self.workspace_root = workspace_root or Path.cwd()
        self.library_root = self.workspace_root / "library"
        self._ensure_directories()
    
    def _ensure_directories(self):
        """Ensure all library directories exist"""
        directories = [
            self.library_root / "images",
            self.library_root / "videos", 
            self.library_root / "audio",
            self.library_root / "documents",
            self.library_root / "3d_models",
            self.library_root / "campaigns",
            self.library_root / "contacts",
            self.library_root / "playground"
        ]
        for dir_path in directories:
            dir_path.mkdir(parents=True, exist_ok=True)
    
    def save_generated_content(
        self,
        content_url: str,
        content_type: str,
        metadata: Dict[str, Any],
        source: str = "unknown"
    ) -> Optional[Path]:
        """
        Save generated content to library and update Otto's memory
        
        Args:
            content_url: URL or path to the generated content
            content_type: Type of content (image, video, audio, 3d, document)
            metadata: Additional metadata (prompt, model, parameters, etc.)
            source: Source of generation (playground, campaign, otto, etc.)
            
        Returns:
            Path to saved file or None if failed
        """
        try:
            # Determine target directory
            type_map = {
                'image': 'images',
                'video': 'videos',
                'audio': 'audio',
                '3d': '3d_models',
                'document': 'documents',
                'campaign': 'campaigns'
            }
            target_dir = self.library_root / type_map.get(content_type, 'playground')
            target_dir.mkdir(parents=True, exist_ok=True)
            
            # Download file if it's a URL
            if content_url.startswith('http'):
                import requests
                response = requests.get(content_url, timeout=60)
                response.raise_for_status()
                content_data = response.content
                
                # Determine file extension from URL or content-type
                if content_url.endswith('.glb'):
                    ext = '.glb'
                elif content_url.endswith('.gltf'):
                    ext = '.gltf'
                elif content_url.endswith('.obj'):
                    ext = '.obj'
                elif content_url.endswith('.mp4'):
                    ext = '.mp4'
                elif content_url.endswith('.mp3'):
                    ext = '.mp3'
                elif content_url.endswith('.wav'):
                    ext = '.wav'
                elif content_url.endswith(('.jpg', '.jpeg')):
                    ext = '.jpg'
                elif content_url.endswith('.png'):
                    ext = '.png'
                elif content_url.endswith('.webp'):
                    ext = '.webp'
                else:
                    # Try to get from content-type header
                    content_type_header = response.headers.get('content-type', '')
                    if 'image/jpeg' in content_type_header:
                        ext = '.jpg'
                    elif 'image/png' in content_type_header:
                        ext = '.png'
                    elif 'video/mp4' in content_type_header:
                        ext = '.mp4'
                    elif 'audio/mpeg' in content_type_header:
                        ext = '.mp3'
                    elif 'model/gltf' in content_type_header:
                        ext = '.glb'
                    else:
                        ext = '.bin'
            else:
                # Local file
                source_path = Path(content_url)
                if not source_path.exists():
                    logger.warning(f"Source file not found: {content_url}")
                    return None
                content_data = source_path.read_bytes()
                ext = source_path.suffix
            
            # Generate filename with timestamp
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            base_name = metadata.get('name', f"{content_type}_{timestamp}")
            # Sanitize filename
            base_name = "".join(c for c in base_name if c.isalnum() or c in (' ', '_', '-')).strip()
            base_name = base_name[:50]  # Limit length
            
            filename = f"{base_name}_{timestamp}{ext}"
            target_path = target_dir / filename
            
            # Save file
            target_path.write_bytes(content_data)
            logger.info(f"💾 Saved {content_type} to library: {target_path}")
            
            # Save metadata JSON
            metadata_path = target_path.with_suffix(target_path.suffix + '.json')
            full_metadata = {
                'filename': filename,
                'content_type': content_type,
                'source': source,
                'source_url': content_url if content_url.startswith('http') else None,
                'created_at': datetime.now().isoformat(),
                'file_size': len(content_data),
                **metadata
            }
            metadata_path.write_text(json.dumps(full_metadata, indent=2))
            
            # Update Otto's memory
            self._update_otto_memory(content_type, target_path, metadata, source)
            
            # Show success notification in UI
            if 'st' in dir() and hasattr(st, 'toast'):
                st.toast(f"✅ Saved {content_type} to library!", icon="💾")
            
            return target_path
            
        except Exception as e:
            logger.error(f"Failed to save content: {e}")
            if 'st' in dir():
                st.warning(f"⚠️ Could not save to library: {e}")
            return None
    
    def _update_otto_memory(
        self,
        content_type: str,
        file_path: Path,
        metadata: Dict,
        source: str
    ):
        """Update Otto's memory with information about generated content"""
        try:
            # Get Otto's session if available
            if 'otto_current_session' not in st.session_state:
                return
            
            session = st.session_state.otto_current_session
            if not session:
                return
            
            # Create memory entry
            memory_text = self._format_memory_entry(content_type, file_path, metadata, source)
            
            # Add to session context
            if not hasattr(session, 'context'):
                session.context = {}
            
            if 'generated_files' not in session.context:
                session.context['generated_files'] = []
            
            session.context['generated_files'].append({
                'type': content_type,
                'path': str(file_path),
                'timestamp': datetime.now().isoformat(),
                'source': source,
                'metadata': metadata
            })
            
            # Add as a system message for context
            session.add_message(
                role='system',
                content=memory_text,
                metadata={'type': 'file_generation', 'auto_tracked': True}
            )
            
            logger.info(f"🧠 Updated Otto memory with {content_type} generation")
            
        except Exception as e:
            logger.warning(f"Could not update Otto memory: {e}")
    
    def _format_memory_entry(
        self,
        content_type: str,
        file_path: Path,
        metadata: Dict,
        source: str
    ) -> str:
        """Format a memory entry for Otto"""
        prompt = metadata.get('prompt', 'N/A')
        model = metadata.get('model', 'N/A')
        
        entry = f"[AUTO] Generated {content_type} via {source}\n"
        entry += f"File: {file_path.name}\n"
        entry += f"Location: library/{file_path.parent.name}/{file_path.name}\n"
        
        if prompt and prompt != 'N/A':
            entry += f"Prompt: {prompt[:200]}...\n" if len(prompt) > 200 else f"Prompt: {prompt}\n"
        
        if model and model != 'N/A':
            entry += f"Model: {model}\n"
        
        # Add key parameters
        params = []
        for key in ['aspect_ratio', 'duration', 'fps', 'resolution', 'style', 'quality']:
            if key in metadata:
                params.append(f"{key}={metadata[key]}")
        
        if params:
            entry += f"Parameters: {', '.join(params)}\n"
        
        return entry


# Global instance
_storage_manager = None


def get_storage_manager() -> UnifiedStorageManager:
    """Get or create the global storage manager instance"""
    global _storage_manager
    if _storage_manager is None:
        _storage_manager = UnifiedStorageManager()
    return _storage_manager


def auto_save_generated_content(
    content_url: str,
    content_type: str,
    source: str,
    **metadata
) -> Optional[Path]:
    """
    Convenience function to auto-save generated content
    
    Usage:
        auto_save_generated_content(
            content_url="https://...",
            content_type="image",
            source="playground",
            prompt="A sunset...",
            model="flux-fast",
            aspect_ratio="16:9"
        )
    """
    manager = get_storage_manager()
    return manager.save_generated_content(content_url, content_type, metadata, source)
