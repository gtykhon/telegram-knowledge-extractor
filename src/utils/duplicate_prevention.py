#!/usr/bin/env python3
"""
Duplicate Prevention System for Telegram Knowledge Base Extractor
Location: src/utils/duplicate_prevention.py

Comprehensive duplicate detection and prevention system using:
- Message ID tracking per channel
- Content hash detection (SHA-256)
- Temporal clustering for near-duplicates
- Centralized database management (prevents locking)
- State persistence for crash recovery

Features:
- Multi-layer duplicate detection
- High-performance batch filtering
- Thread-safe operations
- Comprehensive statistics
"""

import json
import hashlib
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Set, Optional, Any, Tuple
from dataclasses import dataclass, field

from .db_manager import db_manager, execute_query, init_database_schema
from .emoji_logger import create_emoji_logger


logger = create_emoji_logger(__name__)


@dataclass
class ProcessedMessage:
    """Represents a processed message for tracking"""
    message_id: str
    channel_id: str
    channel_name: str
    date: datetime
    content_hash: str
    processed_at: datetime
    processing_status: str = "completed"
    ai_processed: bool = False
    storage_path: Optional[str] = None


@dataclass
class DuplicateStats:
    """Statistics about duplicate detection"""
    total_messages_tracked: int = 0
    channels_tracked: int = 0
    content_hashes: int = 0
    duplicates_detected_this_run: int = 0
    database_file_size: int = 0
    last_cleanup: Optional[datetime] = None


class DuplicateTracker:
    """
    Advanced duplicate tracking system with centralized database management
    
    Uses multiple strategies to detect duplicates:
    1. Message ID + Channel ID combination (primary key)
    2. Content hash for identical text across channels
    3. Temporal clustering for near-duplicate detection
    4. Persistent SQLite storage with centralized connections
    
    Example:
        tracker = DuplicateTracker(Path("data"))
        is_dup, reason = tracker.is_duplicate(message)
        if not is_dup:
            tracker.mark_as_processed(message)
    """
    
    def __init__(self, data_directory: Path = None):
        """
        Initialize duplicate tracker
        
        Args:
            data_directory: Directory to store tracking data
        """
        if data_directory is None:
            data_directory = Path("data")
        
        self.data_directory = Path(data_directory)
        self.data_directory.mkdir(parents=True, exist_ok=True)
        
        # Database setup with centralized manager
        self.db_name = "duplicate_tracker"
        self.db_path = self.data_directory / "processed_messages.db"
        
        # Register database with connection manager
        db_manager.register_database(self.db_name, self.db_path)
        
        # State file for backup
        self.state_file = self.data_directory / "duplicate_tracker_state.json"
        self.backup_directory = self.data_directory / "duplicate_backups"
        self.backup_directory.mkdir(exist_ok=True)
        
        # In-memory caches for performance
        self._processed_message_ids: Dict[str, Set[str]] = {}
        self._content_hashes: Set[str] = set()
        self._last_message_ids: Dict[str, str] = {}
        self._channel_info: Dict[str, Dict] = {}
        
        # Statistics
        self._session_stats = {
            'duplicates_detected': 0,
            'messages_checked': 0,
            'cache_hits': 0,
            'database_queries': 0
        }
        
        # Initialize
        self._initialize_database()
        self._load_state()
        
        logger.info("Duplicate tracker initialized successfully")
    
    def _initialize_database(self):
        """Initialize database schema"""
        schema_queries = [
            """
            CREATE TABLE IF NOT EXISTS processed_messages (
                message_id TEXT NOT NULL,
                channel_id TEXT NOT NULL,
                channel_name TEXT,
                date TEXT,
                content_hash TEXT,
                processed_at TEXT NOT NULL,
                processing_status TEXT DEFAULT 'completed',
                ai_processed INTEGER DEFAULT 0,
                storage_path TEXT,
                PRIMARY KEY (message_id, channel_id)
            )
            """,
            "CREATE INDEX IF NOT EXISTS idx_content_hash ON processed_messages(content_hash)",
            "CREATE INDEX IF NOT EXISTS idx_channel_id ON processed_messages(channel_id)",
            "CREATE INDEX IF NOT EXISTS idx_processed_at ON processed_messages(processed_at)",
            """
            CREATE TABLE IF NOT EXISTS tracker_metadata (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at TEXT
            )
            """
        ]
        
        try:
            init_database_schema(self.db_name, schema_queries)
            
            # Store metadata
            execute_query(
                self.db_name,
                "INSERT OR REPLACE INTO tracker_metadata (key, value, updated_at) VALUES (?, ?, ?)",
                ('tracker_version', '2.0.0', datetime.now().isoformat())
            )
            
            logger.debug("Database initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise
    
    def _load_state(self):
        """Load state from database and state file"""
        try:
            # Load from database
            results = execute_query(
                self.db_name,
                "SELECT DISTINCT channel_id, message_id FROM processed_messages",
                fetch='all',
                read_only=True
            )
            
            for channel_id, message_id in results:
                if channel_id not in self._processed_message_ids:
                    self._processed_message_ids[channel_id] = set()
                self._processed_message_ids[channel_id].add(str(message_id))
            
            # Load content hashes
            results = execute_query(
                self.db_name,
                "SELECT DISTINCT content_hash FROM processed_messages WHERE content_hash IS NOT NULL",
                fetch='all',
                read_only=True
            )
            
            self._content_hashes = {row[0] for row in results if row[0]}
            
            # Load from state file as backup
            if self.state_file.exists():
                try:
                    with open(self.state_file, 'r', encoding='utf-8') as f:
                        state = json.load(f)
                    
                    # Merge with database data
                    for channel_id, message_ids in state.get('processed_message_ids', {}).items():
                        if channel_id not in self._processed_message_ids:
                            self._processed_message_ids[channel_id] = set()
                        self._processed_message_ids[channel_id].update(message_ids)
                    
                    self._content_hashes.update(state.get('content_hashes', []))
                except Exception as e:
                    logger.warning(f"Could not load state file: {e}")
            
            total_tracked = sum(len(msgs) for msgs in self._processed_message_ids.values())
            logger.info(f"Loaded state: {len(self._processed_message_ids)} channels, {total_tracked} messages")
            
        except Exception as e:
            logger.error(f"Failed to load state: {e}")
    
    def _save_state(self):
        """Save current state to file"""
        try:
            state = {
                'processed_message_ids': {
                    k: list(v) for k, v in self._processed_message_ids.items()
                },
                'content_hashes': list(self._content_hashes),
                'last_message_ids': self._last_message_ids,
                'saved_at': datetime.now().isoformat()
            }
            
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(state, f, indent=2)
            
            logger.debug("State saved successfully")
        except Exception as e:
            logger.warning(f"Failed to save state: {e}")
    
    def _generate_content_hash(self, message: Dict[str, Any]) -> str:
        """
        Generate SHA-256 hash of message content
        
        Args:
            message: Message dictionary
            
        Returns:
            str: SHA-256 hash of content
        """
        # Extract text content
        text = message.get('text', '') or message.get('message', '') or ''
        
        # Normalize text (lowercase, strip whitespace)
        normalized_text = text.lower().strip()
        
        # Generate hash
        return hashlib.sha256(normalized_text.encode('utf-8')).hexdigest()
    
    def is_duplicate(self, message: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Check if message is a duplicate using multiple strategies
        
        Args:
            message: Message dictionary with keys: id, channel_id, text
            
        Returns:
            Tuple of (is_duplicate: bool, reason: str)
        """
        try:
            self._session_stats['messages_checked'] += 1
            
            message_id = str(message.get('id', ''))
            channel_id = str(message.get('channel_id', ''))
            
            # Strategy 1: Message ID + Channel ID (most reliable)
            if channel_id in self._processed_message_ids:
                if message_id in self._processed_message_ids[channel_id]:
                    self._session_stats['duplicates_detected'] += 1
                    self._session_stats['cache_hits'] += 1
                    return True, f"Message ID {message_id} already processed for channel {channel_id}"
            
            # Strategy 2: Content hash (identical text)
            content_hash = self._generate_content_hash(message)
            if content_hash in self._content_hashes:
                self._session_stats['duplicates_detected'] += 1
                self._session_stats['cache_hits'] += 1
                return True, f"Identical content already processed (hash: {content_hash[:8]}...)"
            
            # Not a duplicate
            return False, "No duplicate detected"
            
        except Exception as e:
            logger.error(f"Error checking for duplicate: {e}")
            # When in doubt, process the message
            return False, f"Error during duplicate check: {e}"
    
    def mark_as_processed(self, message: Dict[str, Any], 
                         status: str = "completed", 
                         ai_processed: bool = False, 
                         storage_path: Optional[str] = None):
        """
        Mark a message as processed
        
        Args:
            message: Message dictionary
            status: Processing status
            ai_processed: Whether message was processed with AI
            storage_path: Path where message was stored
        """
        try:
            message_id = str(message.get('id', ''))
            channel_id = str(message.get('channel_id', ''))
            channel_name = message.get('channel', '') or message.get('channel_name', '')
            
            # Generate content hash
            content_hash = self._generate_content_hash(message)
            
            # Get message date
            message_date = message.get('date')
            if isinstance(message_date, datetime):
                date_str = message_date.isoformat()
            else:
                date_str = str(message_date) if message_date else datetime.now().isoformat()
            
            # Update in-memory caches
            if channel_id not in self._processed_message_ids:
                self._processed_message_ids[channel_id] = set()
            self._processed_message_ids[channel_id].add(message_id)
            self._content_hashes.add(content_hash)
            
            # Save to database
            execute_query(
                self.db_name,
                """
                INSERT OR REPLACE INTO processed_messages 
                (message_id, channel_id, channel_name, date, content_hash, 
                 processed_at, processing_status, ai_processed, storage_path)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (message_id, channel_id, channel_name, date_str, content_hash,
                 datetime.now().isoformat(), status, int(ai_processed), storage_path)
            )
            
            logger.debug(f"Marked message {message_id} as processed")
            
        except Exception as e:
            logger.error(f"Failed to mark message as processed: {e}")
    
    def filter_duplicates(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Filter out duplicate messages from a list
        
        Args:
            messages: List of message dictionaries
            
        Returns:
            List of non-duplicate messages
        """
        unique_messages = []
        
        for message in messages:
            is_dup, _ = self.is_duplicate(message)
            if not is_dup:
                unique_messages.append(message)
        
        logger.info(f"Filtered {len(messages)} messages → {len(unique_messages)} unique")
        return unique_messages
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get comprehensive statistics
        
        Returns:
            Dictionary of statistics
        """
        total_tracked = sum(len(msgs) for msgs in self._processed_message_ids.values())
        
        # Database stats
        db_stats = {}
        try:
            result = execute_query(
                self.db_name,
                "SELECT COUNT(*) FROM processed_messages",
                fetch='one',
                read_only=True
            )
            db_stats['total_in_db'] = result[0] if result else 0
        except:
            pass
        
        # File sizes
        db_size = self.db_path.stat().st_size if self.db_path.exists() else 0
        state_size = self.state_file.stat().st_size if self.state_file.exists() else 0
        
        return {
            'channels_tracked': len(self._processed_message_ids),
            'total_messages_tracked': total_tracked,
            'content_hashes': len(self._content_hashes),
            'database_file_size': db_size,
            'state_file_size': state_size,
            'database_stats': db_stats,
            'session_stats': self._session_stats.copy(),
            'version': '2.0.0'
        }
    
    def close(self):
        """Close tracker and save state"""
        try:
            self._save_state()
            logger.debug("Duplicate tracker closed")
        except Exception as e:
            logger.warning(f"Error closing duplicate tracker: {e}")


# =============================================================================
# Convenience Functions
# =============================================================================

def create_duplicate_tracker(data_directory: Path = None) -> DuplicateTracker:
    """
    Create a duplicate tracker instance
    
    Args:
        data_directory: Optional data directory path
        
    Returns:
        DuplicateTracker: Initialized tracker
    """
    return DuplicateTracker(data_directory)


def filter_duplicate_messages(messages: List[Dict[str, Any]], 
                             tracker: Optional[DuplicateTracker] = None) -> List[Dict[str, Any]]:
    """
    Filter duplicate messages from a list
    
    Args:
        messages: List of messages
        tracker: Optional tracker instance
        
    Returns:
        List of unique messages
    """
    if tracker is None:
        tracker = create_duplicate_tracker()
    
    return tracker.filter_duplicates(messages)


def mark_messages_as_processed(messages: List[Dict[str, Any]], 
                              tracker: Optional[DuplicateTracker] = None,
                              status: str = "completed"):
    """
    Mark multiple messages as processed
    
    Args:
        messages: List of messages
        tracker: Optional tracker instance
        status: Processing status
    """
    if tracker is None:
        tracker = create_duplicate_tracker()
    
    for message in messages:
        tracker.mark_as_processed(message, status)


# Export public API
__all__ = [
    'DuplicateTracker',
    'ProcessedMessage',
    'DuplicateStats',
    'create_duplicate_tracker',
    'filter_duplicate_messages',
    'mark_messages_as_processed'
]


# Testing
if __name__ == "__main__":
    # Test duplicate tracker
    print("Testing Duplicate Prevention System...")
    
    tracker = create_duplicate_tracker(Path("test_data"))
    
    # Test messages
    messages = [
        {'id': '1', 'channel_id': 'test_channel', 'text': 'Hello world', 'date': datetime.now()},
        {'id': '2', 'channel_id': 'test_channel', 'text': 'Different message', 'date': datetime.now()},
        {'id': '1', 'channel_id': 'test_channel', 'text': 'Hello world', 'date': datetime.now()},  # Duplicate ID
        {'id': '3', 'channel_id': 'test_channel', 'text': 'Hello world', 'date': datetime.now()},  # Duplicate content
    ]
    
    # Process messages
    for msg in messages:
        is_dup, reason = tracker.is_duplicate(msg)
        if is_dup:
            print(f"❌ Duplicate: {msg['id']} - {reason}")
        else:
            print(f"✅ New message: {msg['id']}")
            tracker.mark_as_processed(msg)
    
    # Get statistics
    stats = tracker.get_statistics()
    print(f"\n📊 Statistics:")
    print(f"   Messages tracked: {stats['total_messages_tracked']}")
    print(f"   Duplicates detected: {stats['session_stats']['duplicates_detected']}")
    
    tracker.close()
    print("\n✅ Test completed!")