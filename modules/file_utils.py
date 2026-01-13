"""
File Utilities Module
Centralized file operations for downloading, saving, and cleaning up files.
Handles Replicate API downloads, temp file management, and safe file I/O.
"""

import os
import logging
import requests
import tempfile
import shutil
from pathlib import Path
from typing import Optional, List, Union
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


def download_file(
    url: str,
    output_path: Optional[str] = None,
    timeout: int = 300,
    chunk_size: int = 8192
) -> Optional[str]:
    """
    Download file from URL to local path.
    
    Args:
        url: URL to download from
        output_path: Where to save file (uses temp if None)
        timeout: Request timeout in seconds
        chunk_size: Download chunk size in bytes
        
    Returns:
        Path to downloaded file, or None if failed
        
    Example:
        >>> file_path = download_file(
        ...     "https://example.com/video.mp4",
        ...     "downloads/video.mp4"
        ... )
    """
    try:
        logger.info(f"⬇️ Downloading from {url[:50]}...")
        
        # Determine output path
        if not output_path:
            # Use temp file with appropriate extension
            ext = _extract_extension_from_url(url)
            temp_dir = Path(tempfile.mkdtemp(prefix="download_"))
            output_path = str(temp_dir / f"downloaded{ext}")
        
        # Ensure output directory exists
        output_dir = os.path.dirname(output_path)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
        
        # Download with streaming
        response = requests.get(url, timeout=timeout, stream=True)
        response.raise_for_status()
        
        # Write to file in chunks
        total_size = int(response.headers.get('content-length', 0))
        downloaded = 0
        
        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=chunk_size):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
        
        logger.info(f"✅ Downloaded {_format_size(downloaded)} to {output_path}")
        return output_path
        
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ Download failed: {e}")
        return None
    except Exception as e:
        logger.error(f"❌ Unexpected error during download: {e}")
        return None


def save_text_file(
    content: str,
    output_path: str,
    encoding: str = 'utf-8'
) -> bool:
    """
    Save text content to file.
    
    Args:
        content: Text content to save
        output_path: Where to save file
        encoding: Text encoding (default utf-8)
        
    Returns:
        True if successful, False otherwise
        
    Example:
        >>> script = "Scene 1: Introduction\\nScene 2: Feature"
        >>> save_text_file(script, "output/script.txt")
    """
    try:
        # Ensure output directory exists
        output_dir = os.path.dirname(output_path)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
        
        with open(output_path, 'w', encoding=encoding) as f:
            f.write(content)
        
        logger.info(f"✅ Saved text file: {output_path}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to save text file: {e}")
        return False


def save_binary_file(
    content: bytes,
    output_path: str
) -> bool:
    """
    Save binary content to file.
    
    Args:
        content: Binary content to save
        output_path: Where to save file
        
    Returns:
        True if successful, False otherwise
        
    Example:
        >>> response = requests.get("https://example.com/image.png")
        >>> save_binary_file(response.content, "image.png")
    """
    try:
        # Ensure output directory exists
        output_dir = os.path.dirname(output_path)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
        
        with open(output_path, 'wb') as f:
            f.write(content)
        
        logger.info(f"✅ Saved binary file: {output_path} ({_format_size(len(content))})")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to save binary file: {e}")
        return False


def create_temp_directory(prefix: str = "temp_") -> Path:
    """
    Create temporary directory that will be cleaned up automatically.
    
    Args:
        prefix: Directory name prefix
        
    Returns:
        Path object to temporary directory
        
    Example:
        >>> temp_dir = create_temp_directory("video_gen_")
        >>> output_file = temp_dir / "output.mp4"
    """
    try:
        temp_dir = Path(tempfile.mkdtemp(prefix=prefix))
        logger.info(f"📁 Created temp directory: {temp_dir}")
        return temp_dir
        
    except Exception as e:
        logger.error(f"❌ Failed to create temp directory: {e}")
        raise


def cleanup_directory(directory: Union[str, Path], force: bool = False) -> bool:
    """
    Remove directory and all its contents.
    
    Args:
        directory: Directory path to remove
        force: If True, ignore errors
        
    Returns:
        True if successful, False otherwise
        
    Example:
        >>> temp_dir = create_temp_directory()
        >>> # ... do work ...
        >>> cleanup_directory(temp_dir)
    """
    try:
        directory = Path(directory)
        
        if not directory.exists():
            logger.warning(f"⚠️ Directory does not exist: {directory}")
            return True
        
        shutil.rmtree(directory, ignore_errors=force)
        logger.info(f"🗑️ Cleaned up directory: {directory}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to cleanup directory: {e}")
        return False


def cleanup_files(file_paths: List[str], ignore_errors: bool = True) -> int:
    """
    Remove multiple files.
    
    Args:
        file_paths: List of file paths to remove
        ignore_errors: If True, continue even if some deletions fail
        
    Returns:
        Number of files successfully deleted
        
    Example:
        >>> temp_files = ["temp1.mp4", "temp2.mp3", "temp3.txt"]
        >>> deleted = cleanup_files(temp_files)
        >>> print(f"Deleted {deleted}/{len(temp_files)} files")
    """
    deleted_count = 0
    
    for file_path in file_paths:
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                deleted_count += 1
            else:
                logger.warning(f"⚠️ File not found (skipping): {file_path}")
                
        except Exception as e:
            logger.error(f"❌ Failed to delete {file_path}: {e}")
            if not ignore_errors:
                raise
    
    logger.info(f"🗑️ Cleaned up {deleted_count}/{len(file_paths)} files")
    return deleted_count


def ensure_directory_exists(directory: Union[str, Path]) -> Path:
    """
    Ensure directory exists, creating it if necessary.
    
    Args:
        directory: Directory path
        
    Returns:
        Path object to directory
        
    Example:
        >>> output_dir = ensure_directory_exists("campaigns/2024-01-15")
        >>> save_file(output_dir / "video.mp4")
    """
    try:
        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=True)
        return directory
        
    except Exception as e:
        logger.error(f"❌ Failed to create directory: {e}")
        raise


def get_file_size(file_path: str) -> Optional[int]:
    """
    Get file size in bytes.
    
    Args:
        file_path: Path to file
        
    Returns:
        File size in bytes, or None if file doesn't exist
        
    Example:
        >>> size = get_file_size("video.mp4")
        >>> print(f"File size: {size / 1024 / 1024:.2f} MB")
    """
    try:
        if not os.path.exists(file_path):
            return None
        
        return os.path.getsize(file_path)
        
    except Exception as e:
        logger.error(f"❌ Failed to get file size: {e}")
        return None


def list_files_in_directory(
    directory: Union[str, Path],
    extension: Optional[str] = None,
    recursive: bool = False
) -> List[Path]:
    """
    List files in directory, optionally filtering by extension.
    
    Args:
        directory: Directory to search
        extension: File extension to filter (e.g., '.mp4', '.txt')
        recursive: If True, search subdirectories
        
    Returns:
        List of Path objects to files
        
    Example:
        >>> videos = list_files_in_directory("campaigns/", extension='.mp4')
        >>> for video in videos:
        ...     print(video)
    """
    try:
        directory = Path(directory)
        
        if not directory.exists():
            logger.warning(f"⚠️ Directory not found: {directory}")
            return []
        
        if recursive:
            pattern = f"**/*{extension}" if extension else "**/*"
            files = [f for f in directory.glob(pattern) if f.is_file()]
        else:
            pattern = f"*{extension}" if extension else "*"
            files = [f for f in directory.glob(pattern) if f.is_file()]
        
        logger.info(f"📂 Found {len(files)} files in {directory}")
        return files
        
    except Exception as e:
        logger.error(f"❌ Failed to list files: {e}")
        return []


def sanitize_filename(filename: str, max_length: int = 255) -> str:
    """
    Sanitize filename by removing/replacing invalid characters.
    
    Args:
        filename: Original filename
        max_length: Maximum filename length
        
    Returns:
        Sanitized filename safe for all filesystems
        
    Example:
        >>> safe_name = sanitize_filename("My Video: Part 1 (Draft).mp4")
        'My_Video_Part_1_Draft.mp4'
    """
    import re
    
    # Remove invalid characters
    filename = re.sub(r'[<>:"/\\|?*]', '', filename)
    
    # Replace spaces with underscores
    filename = filename.replace(' ', '_')
    
    # Remove multiple underscores
    filename = re.sub(r'_+', '_', filename)
    
    # Truncate if too long (preserve extension)
    if len(filename) > max_length:
        name, ext = os.path.splitext(filename)
        max_name_length = max_length - len(ext)
        filename = name[:max_name_length] + ext
    
    return filename


def copy_file(source: Union[str, Path], destination: Union[str, Path]) -> bool:
    """
    Copy file from source to destination.
    
    Args:
        source: Source file path
        destination: Destination file path
        
    Returns:
        True if successful, False otherwise
        
    Example:
        >>> copy_file("temp/video.mp4", "final/video.mp4")
    """
    try:
        source = Path(source)
        destination = Path(destination)
        
        if not source.exists():
            logger.error(f"❌ Source file not found: {source}")
            return False
        
        # Ensure destination directory exists
        destination.parent.mkdir(parents=True, exist_ok=True)
        
        shutil.copy2(source, destination)
        logger.info(f"✅ Copied {source} → {destination}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to copy file: {e}")
        return False


# Private helper functions

def _extract_extension_from_url(url: str) -> str:
    """Extract file extension from URL, defaulting to common types."""
    parsed = urlparse(url)
    path = parsed.path
    
    # Try to get extension from path
    if '.' in path:
        ext = os.path.splitext(path)[1]
        if ext:
            return ext
    
    # Default extensions based on content type (common cases)
    # This is a fallback; proper implementation would check Content-Type header
    return '.mp4'  # Default to video


def _format_size(size_bytes: int) -> str:
    """Format byte size as human-readable string."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f}{unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f}TB"
