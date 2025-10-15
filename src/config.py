#!/usr/bin/env python3
"""
Configuration Management for Telegram Knowledge Base Extractor

This module handles all configuration loading, validation, and management
using Pydantic for type safety and environment variables for flexibility.

Features:
- Type-safe configuration with Pydantic
- Environment variable support
- Configuration validation
- Default values with documentation
- Nested configuration structures
"""

import os
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

try:
    from pydantic import Field
    from pydantic_settings import BaseSettings
    PYDANTIC_AVAILABLE = True
except ImportError:
    print("⚠️  Pydantic not installed. Using fallback configuration.")
    PYDANTIC_AVAILABLE = False
    BaseSettings = object
    Field = lambda *args, **kwargs: None

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


# =============================================================================
# Configuration Classes
# =============================================================================

@dataclass
class TelegramConfig:
    """Telegram API configuration"""
    api_id: str
    api_hash: str
    phone: str
    channels: List[str] = field(default_factory=list)
    session_name: str = "extractor_session"
    
    def is_valid(self) -> bool:
        """Validate Telegram configuration"""
        return bool(self.api_id and self.api_hash and self.phone)


@dataclass
class AIConfig:
    """AI processing configuration with Claude and local AI support"""
    anthropic_api_key: str
    model: str = "claude-3-sonnet-20240229"
    max_tokens: int = 300
    temperature: float = 0.2
    processing_delay: int = 1
    
    # Local AI configuration
    use_local_ai: bool = False
    local_ai_primary: bool = False
    ollama_base_url: str = "http://localhost:11434"
    local_models: Dict[str, str] = field(default_factory=lambda: {
        'reasoning': 'deepseek-r1:32b',
        'general': 'llama3.1:8b',
        'efficient': 'phi3:mini',
        'coding': 'codellama:34b',
        'large_context': 'llama3.3:70b'
    })
    
    # Smart model selection
    auto_model_selection: bool = True
    task_routing: Dict[str, str] = field(default_factory=lambda: {
        'summary': 'general',
        'analysis': 'reasoning',
        'quick': 'efficient',
        'code': 'coding',
        'complex': 'reasoning',
        'default': 'general'
    })
    
    # Fallback configuration
    claude_fallback_enabled: bool = True
    max_local_retries: int = 2
    fallback_threshold_tokens: int = 2000
    
    def is_valid(self) -> bool:
        """Check if AI configuration is valid"""
        if not self.use_local_ai and not self.anthropic_api_key:
            return False
        return True
    
    def get_local_model_for_task(self, task_type: str = 'default') -> str:
        """Get the appropriate local model for a task type"""
        model_key = self.task_routing.get(task_type, 'default')
        return self.local_models.get(model_key, self.local_models['general'])


@dataclass
class ProcessingConfig:
    """Message processing configuration"""
    batch_size: int = 50
    max_workers: int = 4
    processing_delay: int = 1
    message_limit_per_channel: int = 1000
    max_message_age_days: int = 30
    
    # Duplicate prevention
    enable_duplicate_prevention: bool = True
    content_hash_enabled: bool = True
    temporal_clustering_enabled: bool = True


@dataclass
class StorageConfig:
    """Data storage configuration"""
    data_directory: str = "./data"
    
    # JSON storage
    enable_json_storage: bool = True
    json_file_path: str = "./data/messages.json"
    
    # CSV export
    enable_csv_export: bool = True
    csv_file_path: str = "./data/exports/messages.csv"
    
    # Google Docs export
    enable_google_docs_export: bool = False
    google_docs_credentials_path: str = "./credentials/google_credentials.json"
    google_docs_folder_id: Optional[str] = None


@dataclass
class NotificationConfig:
    """Notification configuration"""
    enable_notifications: bool = False
    notification_channel: Optional[str] = None
    notify_on_start: bool = True
    notify_on_completion: bool = True
    notify_on_error: bool = True
    notify_batch_summary: bool = True


@dataclass
class LoggingConfig:
    """Logging configuration"""
    log_level: str = "INFO"
    log_file: str = "./logs/extractor.log"
    enable_colored_logs: bool = True
    enable_emoji_logs: bool = True


@dataclass
class DatabaseConfig:
    """Database configuration"""
    db_processed_messages: str = "./data/processed_messages.db"
    db_connection_timeout: int = 30
    db_max_connections_per_db: int = 5
    db_connection_max_age: int = 3600


@dataclass
class PerformanceConfig:
    """Performance and optimization configuration"""
    enable_memory_manager: bool = True
    max_memory_usage_mb: int = 1024
    cache_size_mb: int = 256
    
    # Async settings
    async_semaphore_limit: int = 10
    async_batch_size: int = 20
    
    # Connection pooling
    anthropic_pool_size: int = 5
    openai_pool_size: int = 5


@dataclass
class DebugConfig:
    """Debug and development configuration"""
    debug_mode: bool = False
    dry_run: bool = False
    skip_ai_processing: bool = False
    enable_autonomous_debug: bool = False
    auto_fix_errors: bool = False
    enable_performance_monitoring: bool = True
    monitor_interval_seconds: int = 60


# =============================================================================
# Main Configuration Class
# =============================================================================

@dataclass
class Config:
    """
    Main configuration class aggregating all configuration sections
    
    This class provides a single access point for all application configuration
    """
    telegram: TelegramConfig
    ai: AIConfig
    processing: ProcessingConfig
    storage: StorageConfig
    notification: NotificationConfig
    logging: LoggingConfig
    database: DatabaseConfig
    performance: PerformanceConfig
    debug: DebugConfig
    
    def validate(self) -> bool:
        """Validate the entire configuration"""
        if not self.telegram.is_valid():
            raise ValueError("Invalid Telegram configuration")
        
        if not self.ai.is_valid():
            raise ValueError("Invalid AI configuration")
        
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary"""
        return {
            'telegram': self.telegram.__dict__,
            'ai': self.ai.__dict__,
            'processing': self.processing.__dict__,
            'storage': self.storage.__dict__,
            'notification': self.notification.__dict__,
            'logging': self.logging.__dict__,
            'database': self.database.__dict__,
            'performance': self.performance.__dict__,
            'debug': self.debug.__dict__
        }


# =============================================================================
# Configuration Loading Functions
# =============================================================================

def load_config_from_env() -> Config:
    """
    Load configuration from environment variables
    
    Returns:
        Config: Complete configuration object
    """
    # Telegram configuration
    telegram = TelegramConfig(
        api_id=os.getenv('TELEGRAM_API_ID', ''),
        api_hash=os.getenv('TELEGRAM_API_HASH', ''),
        phone=os.getenv('TELEGRAM_PHONE', ''),
        channels=os.getenv('TELEGRAM_CHANNELS', '').split(',') if os.getenv('TELEGRAM_CHANNELS') else [],
        session_name=os.getenv('TELEGRAM_SESSION_NAME', 'extractor_session')
    )
    
    # AI configuration
    local_models = {
        'reasoning': os.getenv('LOCAL_MODEL_REASONING', 'deepseek-r1:32b'),
        'general': os.getenv('LOCAL_MODEL_GENERAL', 'llama3.1:8b'),
        'efficient': os.getenv('LOCAL_MODEL_EFFICIENT', 'phi3:mini'),
        'coding': os.getenv('LOCAL_MODEL_CODING', 'codellama:34b'),
        'large_context': os.getenv('LOCAL_MODEL_LARGE_CONTEXT', 'llama3.3:70b')
    }
    
    ai = AIConfig(
        anthropic_api_key=os.getenv('ANTHROPIC_API_KEY', ''),
        model=os.getenv('CLAUDE_MODEL', 'claude-3-sonnet-20240229'),
        max_tokens=int(os.getenv('CLAUDE_MAX_TOKENS', '300')),
        temperature=float(os.getenv('CLAUDE_TEMPERATURE', '0.2')),
        processing_delay=int(os.getenv('CLAUDE_PROCESSING_DELAY', '1')),
        use_local_ai=os.getenv('USE_LOCAL_AI', 'false').lower() == 'true',
        local_ai_primary=os.getenv('LOCAL_AI_PRIMARY', 'false').lower() == 'true',
        ollama_base_url=os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434'),
        local_models=local_models,
        claude_fallback_enabled=os.getenv('CLAUDE_FALLBACK_ENABLED', 'true').lower() == 'true',
        max_local_retries=int(os.getenv('MAX_LOCAL_RETRIES', '2')),
        fallback_threshold_tokens=int(os.getenv('FALLBACK_THRESHOLD_TOKENS', '2000'))
    )
    
    # Processing configuration
    processing = ProcessingConfig(
        batch_size=int(os.getenv('BATCH_SIZE', '50')),
        max_workers=int(os.getenv('MAX_WORKERS', '4')),
        processing_delay=int(os.getenv('PROCESSING_DELAY', '1')),
        message_limit_per_channel=int(os.getenv('MESSAGE_LIMIT_PER_CHANNEL', '1000')),
        max_message_age_days=int(os.getenv('MAX_MESSAGE_AGE_DAYS', '30')),
        enable_duplicate_prevention=os.getenv('ENABLE_DUPLICATE_PREVENTION', 'true').lower() == 'true',
        content_hash_enabled=os.getenv('CONTENT_HASH_ENABLED', 'true').lower() == 'true',
        temporal_clustering_enabled=os.getenv('TEMPORAL_CLUSTERING_ENABLED', 'true').lower() == 'true'
    )
    
    # Storage configuration
    storage = StorageConfig(
        data_directory=os.getenv('DATA_DIRECTORY', './data'),
        enable_json_storage=os.getenv('ENABLE_JSON_STORAGE', 'true').lower() == 'true',
        json_file_path=os.getenv('JSON_FILE_PATH', './data/messages.json'),
        enable_csv_export=os.getenv('ENABLE_CSV_EXPORT', 'true').lower() == 'true',
        csv_file_path=os.getenv('CSV_FILE_PATH', './data/exports/messages.csv'),
        enable_google_docs_export=os.getenv('ENABLE_GOOGLE_DOCS_EXPORT', 'false').lower() == 'true',
        google_docs_credentials_path=os.getenv('GOOGLE_DOCS_CREDENTIALS_PATH', './credentials/google_credentials.json'),
        google_docs_folder_id=os.getenv('GOOGLE_DOCS_FOLDER_ID')
    )
    
    # Notification configuration
    notification = NotificationConfig(
        enable_notifications=os.getenv('ENABLE_NOTIFICATIONS', 'false').lower() == 'true',
        notification_channel=os.getenv('NOTIFICATION_CHANNEL'),
        notify_on_start=os.getenv('NOTIFY_ON_START', 'true').lower() == 'true',
        notify_on_completion=os.getenv('NOTIFY_ON_COMPLETION', 'true').lower() == 'true',
        notify_on_error=os.getenv('NOTIFY_ON_ERROR', 'true').lower() == 'true',
        notify_batch_summary=os.getenv('NOTIFY_BATCH_SUMMARY', 'true').lower() == 'true'
    )
    
    # Logging configuration
    logging_config = LoggingConfig(
        log_level=os.getenv('LOG_LEVEL', 'INFO'),
        log_file=os.getenv('LOG_FILE', './logs/extractor.log'),
        enable_colored_logs=os.getenv('ENABLE_COLORED_LOGS', 'true').lower() == 'true',
        enable_emoji_logs=os.getenv('ENABLE_EMOJI_LOGS', 'true').lower() == 'true'
    )
    
    # Database configuration
    database = DatabaseConfig(
        db_processed_messages=os.getenv('DB_PROCESSED_MESSAGES', './data/processed_messages.db'),
        db_connection_timeout=int(os.getenv('DB_CONNECTION_TIMEOUT', '30')),
        db_max_connections_per_db=int(os.getenv('DB_MAX_CONNECTIONS_PER_DB', '5')),
        db_connection_max_age=int(os.getenv('DB_CONNECTION_MAX_AGE', '3600'))
    )
    
    # Performance configuration
    performance = PerformanceConfig(
        enable_memory_manager=os.getenv('ENABLE_MEMORY_MANAGER', 'true').lower() == 'true',
        max_memory_usage_mb=int(os.getenv('MAX_MEMORY_USAGE_MB', '1024')),
        cache_size_mb=int(os.getenv('CACHE_SIZE_MB', '256')),
        async_semaphore_limit=int(os.getenv('ASYNC_SEMAPHORE_LIMIT', '10')),
        async_batch_size=int(os.getenv('ASYNC_BATCH_SIZE', '20')),
        anthropic_pool_size=int(os.getenv('ANTHROPIC_POOL_SIZE', '5')),
        openai_pool_size=int(os.getenv('OPENAI_POOL_SIZE', '5'))
    )
    
    # Debug configuration
    debug = DebugConfig(
        debug_mode=os.getenv('DEBUG_MODE', 'false').lower() == 'true',
        dry_run=os.getenv('DRY_RUN', 'false').lower() == 'true',
        skip_ai_processing=os.getenv('SKIP_AI_PROCESSING', 'false').lower() == 'true',
        enable_autonomous_debug=os.getenv('ENABLE_AUTONOMOUS_DEBUG', 'false').lower() == 'true',
        auto_fix_errors=os.getenv('AUTO_FIX_ERRORS', 'false').lower() == 'true',
        enable_performance_monitoring=os.getenv('ENABLE_PERFORMANCE_MONITORING', 'true').lower() == 'true',
        monitor_interval_seconds=int(os.getenv('MONITOR_INTERVAL_SECONDS', '60'))
    )
    
    # Create main config
    config = Config(
        telegram=telegram,
        ai=ai,
        processing=processing,
        storage=storage,
        notification=notification,
        logging=logging_config,
        database=database,
        performance=performance,
        debug=debug
    )
    
    # Validate configuration
    config.validate()
    
    return config


# =============================================================================
# Global Configuration Access
# =============================================================================

_global_config: Optional[Config] = None


def get_config() -> Config:
    """
    Get the global configuration instance
    
    Returns:
        Config: Global configuration object
    """
    global _global_config
    
    if _global_config is None:
        _global_config = load_config_from_env()
    
    return _global_config


def reload_config() -> Config:
    """
    Reload configuration from environment
    
    Returns:
        Config: Newly loaded configuration
    """
    global _global_config
    _global_config = load_config_from_env()
    return _global_config


# =============================================================================
# Utility Functions
# =============================================================================

def print_config_summary(config: Optional[Config] = None):
    """Print a summary of the current configuration"""
    if config is None:
        config = get_config()
    
    print("=" * 60)
    print("TELEGRAM KNOWLEDGE BASE EXTRACTOR - CONFIGURATION")
    print("=" * 60)
    print(f"Telegram Channels: {len(config.telegram.channels)}")
    print(f"AI Provider: {'Local' if config.ai.local_ai_primary else 'Claude'}")
    print(f"Batch Size: {config.processing.batch_size}")
    print(f"Duplicate Prevention: {'Enabled' if config.processing.enable_duplicate_prevention else 'Disabled'}")
    print(f"JSON Storage: {'Enabled' if config.storage.enable_json_storage else 'Disabled'}")
    print(f"CSV Export: {'Enabled' if config.storage.enable_csv_export else 'Disabled'}")
    print(f"Debug Mode: {'Enabled' if config.debug.debug_mode else 'Disabled'}")
    print("=" * 60)


if __name__ == "__main__":
    # Test configuration loading
    try:
        config = get_config()
        print_config_summary(config)
        print("\n✅ Configuration loaded successfully!")
    except Exception as e:
        print(f"\n❌ Configuration error: {e}")