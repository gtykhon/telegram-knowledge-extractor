#!/usr/bin/env python3
"""
Centralized Database Connection Manager
Location: src/utils/db_manager.py

This module provides a centralized SQLite connection manager to prevent
database locking issues by managing all database connections through
a single point with proper connection pooling and cleanup.

Features:
- Singleton pattern for global connection management
- Connection pooling with automatic reuse
- Thread-safe connection handling
- Automatic connection cleanup
- Timeout and retry logic
- Connection statistics and monitoring
"""

import sqlite3
import asyncio
import logging
import threading
import time
from pathlib import Path
from typing import Dict, Optional, Any, List, Tuple
from contextlib import contextmanager, asynccontextmanager
from dataclasses import dataclass
from datetime import datetime


logger = logging.getLogger(__name__)


@dataclass
class ConnectionInfo:
    """Information about a database connection"""
    connection: sqlite3.Connection
    created_at: datetime
    last_used: datetime
    thread_id: int
    is_busy: bool = False
    usage_count: int = 0


class DatabaseConnectionManager:
    """
    Centralized SQLite connection manager with connection pooling
    
    This manager prevents database locking issues by:
    1. Using a single connection pool for all components
    2. Proper connection cleanup and resource management
    3. Thread-safe connection handling
    4. Connection timeout and retry logic
    5. Automatic connection reuse and cleanup
    
    Usage:
        # Register database
        db_manager.register_database("my_db", Path("data/my_db.db"))
        
        # Use connection
        with db_manager.get_connection("my_db") as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM table")
            results = cursor.fetchall()
    """
    
    _instance = None
    _lock = threading.RLock()
    
    def __new__(cls):
        """Singleton pattern to ensure only one connection manager"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(DatabaseConnectionManager, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if getattr(self, '_initialized', False):
            return
            
        self.connections: Dict[str, ConnectionInfo] = {}
        self.db_paths: Dict[str, Path] = {}
        self.connection_timeout = 30.0
        self.max_retries = 3
        self.retry_delay = 1.0
        self.max_connections_per_db = 5
        self.connection_max_age = 3600  # 1 hour
        self._cleanup_interval = 300  # 5 minutes
        self._last_cleanup = time.time()
        self._initialized = True
        
        logger.info("Database Connection Manager initialized")
    
    def register_database(self, db_name: str, db_path: Path) -> None:
        """
        Register a database for connection management
        
        Args:
            db_name: Unique name for the database
            db_path: Path to the SQLite database file
        """
        with self._lock:
            self.db_paths[db_name] = Path(db_path)
            logger.debug(f"Registered database '{db_name}' at {db_path}")
    
    @contextmanager
    def get_connection(self, db_name: str, read_only: bool = False):
        """
        Get a database connection with automatic cleanup
        
        Args:
            db_name: Name of the database
            read_only: Whether this is a read-only connection
            
        Yields:
            sqlite3.Connection: Database connection
        """
        connection = None
        connection_key = None
        
        try:
            connection_key, connection = self._acquire_connection(db_name, read_only)
            yield connection
            
        except Exception as e:
            if connection:
                try:
                    connection.rollback()
                except:
                    pass
            raise e
            
        finally:
            if connection_key and connection:
                self._release_connection(connection_key, connection)
    
    @asynccontextmanager
    async def get_async_connection(self, db_name: str, read_only: bool = False):
        """
        Async version of get_connection
        
        Args:
            db_name: Name of the database
            read_only: Whether this is a read-only connection
            
        Yields:
            sqlite3.Connection: Database connection
        """
        connection = None
        connection_key = None
        
        try:
            # Run connection acquisition in thread pool to avoid blocking
            connection_key, connection = await asyncio.get_event_loop().run_in_executor(
                None, 
                lambda: self._acquire_connection(db_name, read_only)
            )
            yield connection
            
        except Exception as e:
            if connection:
                try:
                    connection.rollback()
                except:
                    pass
            raise e
            
        finally:
            if connection_key and connection:
                await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: self._release_connection(connection_key, connection)
                )
    
    def _acquire_connection(self, db_name: str, read_only: bool = False) -> Tuple[str, sqlite3.Connection]:
        """
        Acquire a database connection from the pool
        
        Args:
            db_name: Database name
            read_only: Whether this is a read-only connection
            
        Returns:
            Tuple of (connection_key, connection)
        """
        if db_name not in self.db_paths:
            raise ValueError(f"Database '{db_name}' not registered")
        
        db_path = self.db_paths[db_name]
        thread_id = threading.get_ident()
        
        # Clean up old connections periodically
        self._periodic_cleanup()
        
        # Try to get existing connection for this thread
        connection_key = f"{db_name}_{thread_id}"
        
        with self._lock:
            if connection_key in self.connections:
                conn_info = self.connections[connection_key]
                if not conn_info.is_busy:
                    conn_info.is_busy = True
                    conn_info.last_used = datetime.now()
                    conn_info.usage_count += 1
                    return connection_key, conn_info.connection
            
            # Create new connection
            for attempt in range(self.max_retries):
                try:
                    # Ensure parent directory exists
                    db_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    # Create connection with appropriate settings
                    connection = sqlite3.Connection(
                        str(db_path),
                        timeout=self.connection_timeout,
                        check_same_thread=False
                    )
                    
                    # Set pragmas for better performance and reliability
                    connection.execute("PRAGMA journal_mode=WAL")
                    connection.execute("PRAGMA synchronous=NORMAL")
                    connection.execute("PRAGMA foreign_keys=ON")
                    connection.execute("PRAGMA busy_timeout=30000")
                    
                    if read_only:
                        connection.execute("PRAGMA query_only=ON")
                    
                    # Store connection info
                    conn_info = ConnectionInfo(
                        connection=connection,
                        created_at=datetime.now(),
                        last_used=datetime.now(),
                        thread_id=thread_id,
                        is_busy=True,
                        usage_count=1
                    )
                    
                    self.connections[connection_key] = conn_info
                    logger.debug(f"Created new connection for '{db_name}' (attempt {attempt + 1})")
                    
                    return connection_key, connection
                    
                except sqlite3.OperationalError as e:
                    if attempt < self.max_retries - 1:
                        logger.warning(f"Database locked, retrying ({attempt + 1}/{self.max_retries})")
                        time.sleep(self.retry_delay)
                    else:
                        logger.error(f"Failed to acquire connection after {self.max_retries} attempts")
                        raise e
    
    def _release_connection(self, connection_key: str, connection: sqlite3.Connection):
        """
        Release a connection back to the pool
        
        Args:
            connection_key: Connection identifier
            connection: Database connection
        """
        with self._lock:
            if connection_key in self.connections:
                conn_info = self.connections[connection_key]
                conn_info.is_busy = False
                conn_info.last_used = datetime.now()
                
                # Commit any pending transactions
                try:
                    connection.commit()
                except:
                    pass
    
    def _periodic_cleanup(self):
        """Periodically clean up old connections"""
        current_time = time.time()
        
        if current_time - self._last_cleanup < self._cleanup_interval:
            return
        
        self._last_cleanup = current_time
        
        with self._lock:
            keys_to_remove = []
            
            for key, conn_info in self.connections.items():
                # Remove old, unused connections
                age = (datetime.now() - conn_info.last_used).total_seconds()
                
                if not conn_info.is_busy and age > self.connection_max_age:
                    try:
                        conn_info.connection.close()
                        keys_to_remove.append(key)
                        logger.debug(f"Cleaned up old connection '{key}'")
                    except:
                        pass
            
            for key in keys_to_remove:
                del self.connections[key]
    
    def close_all_connections(self):
        """Close all connections in the pool"""
        with self._lock:
            for key, conn_info in self.connections.items():
                try:
                    conn_info.connection.close()
                    logger.debug(f"Closed connection '{key}'")
                except:
                    pass
            
            self.connections.clear()
            logger.info("All database connections closed")
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get connection pool statistics
        
        Returns:
            Dict containing connection statistics
        """
        with self._lock:
            stats = {
                'total_connections': len(self.connections),
                'busy_connections': sum(1 for c in self.connections.values() if c.is_busy),
                'registered_databases': len(self.db_paths),
                'connections_by_db': {}
            }
            
            for key, conn_info in self.connections.items():
                db_name = key.split('_')[0]
                if db_name not in stats['connections_by_db']:
                    stats['connections_by_db'][db_name] = 0
                stats['connections_by_db'][db_name] += 1
            
            return stats


# Global connection manager instance
db_manager = DatabaseConnectionManager()


# =============================================================================
# Convenience Functions
# =============================================================================

def execute_query(db_name: str, query: str, params: tuple = (), 
                 fetch: Optional[str] = None, read_only: bool = False):
    """
    Execute a query with automatic connection management
    
    Args:
        db_name: Database name
        query: SQL query
        params: Query parameters
        fetch: 'one', 'all', or None
        read_only: Whether this is a read-only query
        
    Returns:
        Query results or row count
    """
    with db_manager.get_connection(db_name, read_only) as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        
        if fetch == 'one':
            return cursor.fetchone()
        elif fetch == 'all':
            return cursor.fetchall()
        elif query.strip().upper().startswith('SELECT'):
            return cursor.fetchall()
        else:
            return cursor.rowcount


async def execute_query_async(db_name: str, query: str, params: tuple = (), 
                              fetch: Optional[str] = None, read_only: bool = False):
    """
    Async version of execute_query
    
    Args:
        db_name: Database name
        query: SQL query
        params: Query parameters
        fetch: 'one', 'all', or None
        read_only: Whether this is a read-only query
        
    Returns:
        Query results or row count
    """
    async with db_manager.get_async_connection(db_name, read_only) as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        
        if fetch == 'one':
            return cursor.fetchone()
        elif fetch == 'all':
            return cursor.fetchall()
        elif query.strip().upper().startswith('SELECT'):
            return cursor.fetchall()
        else:
            return cursor.rowcount


def init_database_schema(db_name: str, schema_queries: List[str]):
    """
    Initialize database schema with proper connection management
    
    Args:
        db_name: Database name
        schema_queries: List of SQL queries to create schema
    """
    with db_manager.get_connection(db_name) as conn:
        for query in schema_queries:
            conn.execute(query)
        logger.info(f"Initialized schema for database '{db_name}'")


@contextmanager
def batch_operation(db_name: str):
    """
    Context manager for batch database operations
    
    Args:
        db_name: Database name
        
    Yields:
        sqlite3.Connection: Database connection in transaction
    """
    with db_manager.get_connection(db_name) as conn:
        conn.execute("BEGIN TRANSACTION")
        try:
            yield conn
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise


@asynccontextmanager
async def batch_operation_async(db_name: str):
    """
    Async context manager for batch database operations
    
    Args:
        db_name: Database name
        
    Yields:
        sqlite3.Connection: Database connection in transaction
    """
    async with db_manager.get_async_connection(db_name) as conn:
        conn.execute("BEGIN TRANSACTION")
        try:
            yield conn
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise


# =============================================================================
# Testing and Utilities
# =============================================================================

def test_connection(db_name: str) -> bool:
    """
    Test database connection
    
    Args:
        db_name: Database name
        
    Returns:
        bool: True if connection successful
    """
    try:
        with db_manager.get_connection(db_name) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            return result is not None
    except Exception as e:
        logger.error(f"Connection test failed for '{db_name}': {e}")
        return False


if __name__ == "__main__":
    # Test the database manager
    from pathlib import Path
    
    # Create test database
    test_db = Path("test_db.db")
    db_manager.register_database("test", test_db)
    
    # Test connection
    if test_connection("test"):
        print("✅ Database connection successful")
    else:
        print("❌ Database connection failed")
    
    # Test query execution
    execute_query("test", "CREATE TABLE IF NOT EXISTS test (id INTEGER PRIMARY KEY, value TEXT)")
    execute_query("test", "INSERT INTO test (value) VALUES (?)", ("test_value",))
    result = execute_query("test", "SELECT * FROM test", fetch='all')
    print(f"Query result: {result}")
    
    # Get statistics
    stats = db_manager.get_stats()
    print(f"Connection stats: {stats}")
    
    # Cleanup
    db_manager.close_all_connections()
    if test_db.exists():
        test_db.unlink()
    print("✅ Test completed")