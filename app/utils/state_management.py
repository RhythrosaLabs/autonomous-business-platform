"""
Autosave and state recovery system
Provides automatic state persistence, crash recovery, and transaction rollback
"""

import json
import pickle
import shutil
import logging
from pathlib import Path
from typing import Any, Dict, Optional, List, Callable
from datetime import datetime
from dataclasses import dataclass, asdict
import threading
import time

logger = logging.getLogger(__name__)


@dataclass
class SavedState:
    """Saved state snapshot"""
    timestamp: str
    state_data: Dict[str, Any]
    operation: str
    checkpoint_id: str
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'SavedState':
        return cls(**data)


class AutosaveManager:
    """
    Manages automatic state saving and recovery
    Saves state periodically and on critical operations
    """
    
    def __init__(
        self,
        save_dir: Path = None,
        autosave_interval: float = 60.0,  # seconds
        max_autosaves: int = 10
    ):
        self.save_dir = save_dir or Path.home() / ".autonomous_business_platform" / "autosave"
        self.save_dir.mkdir(parents=True, exist_ok=True)
        
        self.autosave_interval = autosave_interval
        self.max_autosaves = max_autosaves
        
        self.last_save_time = None
        self.autosave_thread = None
        self.stop_autosave = threading.Event()
        
        self._state_callbacks: List[Callable] = []
    
    def start_autosave(self):
        """Start automatic saving in background"""
        if self.autosave_thread and self.autosave_thread.is_alive():
            return
        
        self.stop_autosave.clear()
        self.autosave_thread = threading.Thread(target=self._autosave_loop, daemon=True)
        self.autosave_thread.start()
        logger.info(f"Autosave started (interval: {self.autosave_interval}s)")
    
    def stop_autosave_thread(self):
        """Stop autosave thread"""
        self.stop_autosave.set()
        if self.autosave_thread:
            self.autosave_thread.join(timeout=5)
    
    def register_state_callback(self, callback: Callable[[], Dict[str, Any]]):
        """Register a callback that returns state to save"""
        self._state_callbacks.append(callback)
    
    def save_state(
        self,
        state_data: Dict[str, Any],
        operation: str = "manual",
        checkpoint_id: str = None
    ) -> Path:
        """
        Save current state
        
        Args:
            state_data: Dictionary of state to save
            operation: Name of operation being saved
            checkpoint_id: Optional checkpoint identifier
        
        Returns:
            Path to saved file
        """
        if checkpoint_id is None:
            checkpoint_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        saved_state = SavedState(
            timestamp=datetime.now().isoformat(),
            state_data=state_data,
            operation=operation,
            checkpoint_id=checkpoint_id
        )
        
        filename = f"autosave_{checkpoint_id}.json"
        filepath = self.save_dir / filename
        
        try:
            with open(filepath, 'w') as f:
                json.dump(saved_state.to_dict(), f, indent=2, default=str)
            
            self.last_save_time = datetime.now()
            logger.info(f"State saved: {operation} → {filepath}")
            
            # Clean up old saves
            self._cleanup_old_saves()
            
            return filepath
        
        except Exception as e:
            logger.error(f"Failed to save state: {str(e)}")
            raise
    
    def load_latest_state(self) -> Optional[SavedState]:
        """Load most recent saved state"""
        try:
            save_files = sorted(self.save_dir.glob("autosave_*.json"), reverse=True)
            
            if not save_files:
                return None
            
            with open(save_files[0], 'r') as f:
                data = json.load(f)
            
            return SavedState.from_dict(data)
        
        except Exception as e:
            logger.error(f"Failed to load state: {str(e)}")
            return None
    
    def list_saved_states(self) -> List[SavedState]:
        """Get list of all saved states"""
        states = []
        
        for filepath in sorted(self.save_dir.glob("autosave_*.json"), reverse=True):
            try:
                with open(filepath, 'r') as f:
                    data = json.load(f)
                states.append(SavedState.from_dict(data))
            except Exception as e:
                logger.warning(f"Failed to load {filepath}: {str(e)}")
        
        return states
    
    def delete_saved_state(self, checkpoint_id: str):
        """Delete a specific saved state"""
        filepath = self.save_dir / f"autosave_{checkpoint_id}.json"
        if filepath.exists():
            filepath.unlink()
            logger.info(f"Deleted saved state: {checkpoint_id}")
    
    def _autosave_loop(self):
        """Background autosave loop"""
        while not self.stop_autosave.is_set():
            time.sleep(self.autosave_interval)
            
            if self.stop_autosave.is_set():
                break
            
            try:
                # Collect state from all registered callbacks
                state_data = {}
                for callback in self._state_callbacks:
                    try:
                        state_data.update(callback())
                    except Exception as e:
                        logger.warning(f"State callback failed: {str(e)}")
                
                if state_data:
                    self.save_state(state_data, operation="autosave")
            
            except Exception as e:
                logger.error(f"Autosave failed: {str(e)}")
    
    def _cleanup_old_saves(self):
        """Remove old autosaves beyond max limit"""
        save_files = sorted(self.save_dir.glob("autosave_*.json"), reverse=True)
        
        for old_file in save_files[self.max_autosaves:]:
            try:
                old_file.unlink()
                logger.debug(f"Deleted old autosave: {old_file}")
            except Exception as e:
                logger.warning(f"Failed to delete {old_file}: {str(e)}")


class TransactionManager:
    """
    Manages transactional operations with rollback capability
    Useful for file operations that need to be atomic
    """
    
    def __init__(self, workspace_dir: Path = None):
        self.workspace_dir = workspace_dir or Path.cwd()
        self.backup_dir = self.workspace_dir / ".transaction_backups"
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        self.transaction_id = None
        self.backed_up_files: Dict[Path, Path] = {}
        self.created_files: List[Path] = []
        self.deleted_files: Dict[Path, Path] = {}
    
    def begin_transaction(self, transaction_id: str = None):
        """Start a new transaction"""
        self.transaction_id = transaction_id or datetime.now().strftime("%Y%m%d_%H%M%S")
        self.backed_up_files.clear()
        self.created_files.clear()
        self.deleted_files.clear()
        logger.info(f"Transaction started: {self.transaction_id}")
    
    def create_file(self, filepath: Path, content: Any = None):
        """Create a file within transaction"""
        if filepath.exists():
            raise FileExistsError(f"File already exists: {filepath}")
        
        # Create parent directories
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        # Write content
        if content is not None:
            if isinstance(content, (str, bytes)):
                mode = 'wb' if isinstance(content, bytes) else 'w'
                with open(filepath, mode) as f:
                    f.write(content)
            else:
                with open(filepath, 'w') as f:
                    json.dump(content, f, indent=2, default=str)
        else:
            filepath.touch()
        
        self.created_files.append(filepath)
        logger.debug(f"Transaction create: {filepath}")
    
    def modify_file(self, filepath: Path, new_content: Any):
        """Modify a file within transaction (with backup)"""
        if not filepath.exists():
            raise FileNotFoundError(f"File not found: {filepath}")
        
        # Backup original if not already backed up
        if filepath not in self.backed_up_files:
            backup_path = self._create_backup(filepath)
            self.backed_up_files[filepath] = backup_path
        
        # Write new content
        if isinstance(new_content, (str, bytes)):
            mode = 'wb' if isinstance(new_content, bytes) else 'w'
            with open(filepath, mode) as f:
                f.write(new_content)
        else:
            with open(filepath, 'w') as f:
                json.dump(new_content, f, indent=2, default=str)
        
        logger.debug(f"Transaction modify: {filepath}")
    
    def delete_file(self, filepath: Path):
        """Delete a file within transaction (with backup)"""
        if not filepath.exists():
            return  # Already deleted
        
        # Backup before deletion
        backup_path = self._create_backup(filepath)
        self.deleted_files[filepath] = backup_path
        
        # Delete
        filepath.unlink()
        logger.debug(f"Transaction delete: {filepath}")
    
    def commit(self):
        """Commit transaction and cleanup backups"""
        logger.info(f"Transaction committed: {self.transaction_id}")
        self._cleanup_backups()
        self._reset()
    
    def rollback(self):
        """Rollback transaction - undo all changes"""
        logger.warning(f"Transaction rollback: {self.transaction_id}")
        
        try:
            # Remove created files
            for filepath in self.created_files:
                if filepath.exists():
                    filepath.unlink()
                    logger.debug(f"Rollback: removed {filepath}")
            
            # Restore modified files
            for original_path, backup_path in self.backed_up_files.items():
                shutil.copy2(backup_path, original_path)
                logger.debug(f"Rollback: restored {original_path}")
            
            # Restore deleted files
            for original_path, backup_path in self.deleted_files.items():
                shutil.copy2(backup_path, original_path)
                logger.debug(f"Rollback: undeleted {original_path}")
            
            logger.info("Transaction rollback completed")
        
        except Exception as e:
            logger.error(f"Rollback failed: {str(e)}")
            raise
        
        finally:
            self._cleanup_backups()
            self._reset()
    
    def _create_backup(self, filepath: Path) -> Path:
        """Create backup of a file"""
        backup_path = self.backup_dir / f"{self.transaction_id}_{filepath.name}"
        shutil.copy2(filepath, backup_path)
        return backup_path
    
    def _cleanup_backups(self):
        """Remove backup files for this transaction"""
        pattern = f"{self.transaction_id}_*"
        for backup_file in self.backup_dir.glob(pattern):
            try:
                backup_file.unlink()
            except Exception as e:
                logger.warning(f"Failed to delete backup {backup_file}: {str(e)}")
    
    def _reset(self):
        """Reset transaction state"""
        self.transaction_id = None
        self.backed_up_files.clear()
        self.created_files.clear()
        self.deleted_files.clear()


class CrashRecovery:
    """Handles crash detection and recovery"""
    
    def __init__(self, recovery_file: Path = None):
        self.recovery_file = recovery_file or Path.home() / ".autonomous_business_platform" / "crash_recovery.json"
        self.recovery_file.parent.mkdir(parents=True, exist_ok=True)
    
    def mark_operation_start(self, operation_name: str, context: Dict[str, Any] = None):
        """Mark start of a critical operation"""
        recovery_data = {
            'operation': operation_name,
            'start_time': datetime.now().isoformat(),
            'context': context or {},
            'in_progress': True
        }
        
        with open(self.recovery_file, 'w') as f:
            json.dump(recovery_data, f, indent=2, default=str)
    
    def mark_operation_complete(self):
        """Mark operation as successfully completed"""
        if self.recovery_file.exists():
            self.recovery_file.unlink()
    
    def check_for_crash(self) -> Optional[Dict[str, Any]]:
        """Check if there was a crash during last operation"""
        if not self.recovery_file.exists():
            return None
        
        try:
            with open(self.recovery_file, 'r') as f:
                recovery_data = json.load(f)
            
            if recovery_data.get('in_progress'):
                return recovery_data
        
        except Exception as e:
            logger.error(f"Failed to read recovery data: {str(e)}")
        
        return None
    
    def clear_crash_data(self):
        """Clear crash recovery data"""
        if self.recovery_file.exists():
            self.recovery_file.unlink()


# Global instances
_autosave_manager = None
_crash_recovery = None


def get_autosave_manager() -> AutosaveManager:
    """Get global autosave manager instance"""
    global _autosave_manager
    if _autosave_manager is None:
        _autosave_manager = AutosaveManager()
    return _autosave_manager


def get_crash_recovery() -> CrashRecovery:
    """Get global crash recovery instance"""
    global _crash_recovery
    if _crash_recovery is None:
        _crash_recovery = CrashRecovery()
    return _crash_recovery
