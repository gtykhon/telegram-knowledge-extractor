#!/usr/bin/env python3
"""
Enhanced Logging with Emoji Support
Location: src/utils/emoji_logger.py

Provides colorful, emoji-enhanced logging for better readability
and debugging experience.

Features:
- Emoji icons for different log levels
- Color-coded output
- Structured formatting
- Performance-friendly
"""

import logging
import sys
from typing import Optional
from pathlib import Path


# Emoji mapping for log levels and categories
EMOJI_MAP = {
    # Log levels
    'debug': '🔍',
    'info': 'ℹ️',
    'warning': '⚠️',
    'error': '❌',
    'critical': '🚨',
    
    # Status indicators
    'success': '✅',
    'failure': '❌',
    'pending': '⏳',
    'running': '🏃',
    'completed': '🎉',
    
    # Components
    'telegram': '📱',
    'database': '💾',
    'ai': '🤖',
    'network': '🌐',
    'file': '📄',
    'folder': '📁',
    'lock': '🔒',
    'unlock': '🔓',
    
    # Actions
    'search': '🔎',
    'download': '⬇️',
    'upload': '⬆️',
    'process': '⚙️',
    'clean': '🧹',
    'config': '⚙️',
    'start': '▶️',
    'stop': '⏹️',
    'pause': '⏸️',
    
    # Data
    'message': '💬',
    'channel': '📡',
    'user': '👤',
    'group': '👥',
    'stats': '📊',
    'chart': '📈',
    'time': '⏰',
    'calendar': '📅',
    
    # Results
    'check': '✓',
    'cross': '✗',
    'arrow': '→',
    'bullet': '•',
    'star': '⭐',
    'fire': '🔥',
    'rocket': '🚀',
    'lightning': '⚡',
}


class EmojiFormatter(logging.Formatter):
    """Custom formatter with emoji and color support"""
    
    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
        'RESET': '\033[0m',       # Reset
    }
    
    def __init__(self, use_colors: bool = True, use_emojis: bool = True):
        super().__init__()
        self.use_colors = use_colors
        self.use_emojis = use_emojis
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record with emojis and colors"""
        
        # Get emoji for log level
        emoji = ''
        if self.use_emojis:
            emoji_key = record.levelname.lower()
            emoji = EMOJI_MAP.get(emoji_key, '') + ' '
        
        # Get color for log level
        color_start = ''
        color_end = ''
        if self.use_colors and sys.stdout.isatty():
            color_start = self.COLORS.get(record.levelname, '')
            color_end = self.COLORS['RESET']
        
        # Format timestamp
        timestamp = self.formatTime(record, '%Y-%m-%d %H:%M:%S')
        
        # Format message
        message = record.getMessage()
        
        # Build formatted log string
        log_fmt = f"{color_start}{emoji}{timestamp} - {record.name} - {record.levelname}{color_end} - {message}"
        
        # Add exception info if present
        if record.exc_info:
            log_fmt += '\n' + self.formatException(record.exc_info)
        
        return log_fmt


def create_emoji_logger(
    name: str,
    level: int = logging.INFO,
    log_file: Optional[Path] = None,
    use_colors: bool = True,
    use_emojis: bool = True
) -> logging.Logger:
    """
    Create a logger with emoji and color support
    
    Args:
        name: Logger name
        level: Logging level (default: INFO)
        log_file: Optional file path for file logging
        use_colors: Enable colored output (default: True)
        use_emojis: Enable emoji icons (default: True)
        
    Returns:
        logging.Logger: Configured logger instance
        
    Example:
        >>> logger = create_emoji_logger(__name__)
        >>> logger.info("Processing started")
        ℹ️ 2025-01-15 10:30:00 - module - INFO - Processing started
    """
    
    # Get or create logger
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Avoid adding duplicate handlers
    if logger.handlers:
        return logger
    
    # Console handler with emoji formatter
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_formatter = EmojiFormatter(use_colors=use_colors, use_emojis=use_emojis)
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # File handler (optional, no colors/emojis)
    if log_file:
        log_file = Path(log_file)
        log_file.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(level)
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
    
    # Prevent propagation to root logger
    logger.propagate = False
    
    return logger


def get_emoji(key: str) -> str:
    """
    Get emoji by key
    
    Args:
        key: Emoji key
        
    Returns:
        str: Emoji character or empty string if not found
    """
    return EMOJI_MAP.get(key.lower(), '')


# Convenience functions for common patterns
def log_with_emoji(logger: logging.Logger, level: str, emoji_key: str, message: str):
    """
    Log message with custom emoji
    
    Args:
        logger: Logger instance
        level: Log level ('debug', 'info', 'warning', 'error', 'critical')
        emoji_key: Emoji key from EMOJI_MAP
        message: Log message
    """
    emoji = get_emoji(emoji_key)
    log_func = getattr(logger, level.lower())
    log_func(f"{emoji} {message}" if emoji else message)


def log_section(logger: logging.Logger, title: str, width: int = 60):
    """
    Log a section header
    
    Args:
        logger: Logger instance
        title: Section title
        width: Width of the separator line
    """
    logger.info("=" * width)
    logger.info(title.center(width))
    logger.info("=" * width)


def log_subsection(logger: logging.Logger, title: str, width: int = 60):
    """
    Log a subsection header
    
    Args:
        logger: Logger instance
        title: Subsection title
        width: Width of the separator line
    """
    logger.info("-" * width)
    logger.info(title)
    logger.info("-" * width)


def log_progress(logger: logging.Logger, current: int, total: int, prefix: str = "Progress"):
    """
    Log progress information
    
    Args:
        logger: Logger instance
        current: Current progress count
        total: Total count
        prefix: Progress message prefix
    """
    percentage = (current / total * 100) if total > 0 else 0
    logger.info(f"{prefix}: {current}/{total} ({percentage:.1f}%)")


def log_stats(logger: logging.Logger, stats: dict, title: str = "Statistics"):
    """
    Log statistics in a formatted way
    
    Args:
        logger: Logger instance
        stats: Dictionary of statistics
        title: Statistics title
    """
    logger.info(f"\n{title}:")
    for key, value in stats.items():
        logger.info(f"  {key}: {value}")


# Setup basic logging configuration
def setup_logging(
    level: str = "INFO",
    log_file: Optional[Path] = None,
    use_colors: bool = True,
    use_emojis: bool = True
):
    """
    Setup global logging configuration
    
    Args:
        level: Logging level string
        log_file: Optional log file path
        use_colors: Enable colored output
        use_emojis: Enable emoji icons
    """
    
    # Convert level string to logging constant
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # Add console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    console_formatter = EmojiFormatter(use_colors=use_colors, use_emojis=use_emojis)
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)
    
    # Add file handler if specified
    if log_file:
        log_file = Path(log_file)
        log_file.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(numeric_level)
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)


# Example usage and testing
if __name__ == "__main__":
    # Create logger
    logger = create_emoji_logger(__name__, level=logging.DEBUG)
    
    # Test different log levels
    logger.debug("This is a debug message")
    logger.info("This is an info message")
    logger.warning("This is a warning message")
    logger.error("This is an error message")
    logger.critical("This is a critical message")
    
    # Test section logging
    log_section(logger, "Testing Section Headers")
    
    # Test custom emojis
    log_with_emoji(logger, 'info', 'rocket', "Launch successful!")
    log_with_emoji(logger, 'info', 'database', "Database connected")
    log_with_emoji(logger, 'info', 'ai', "AI model loaded")
    
    # Test progress logging
    for i in range(1, 6):
        log_progress(logger, i, 5, "Processing items")
    
    # Test statistics logging
    stats = {
        'Total Messages': 1000,
        'New Messages': 250,
        'Duplicates': 750,
        'Processing Time': '5.2s'
    }
    log_stats(logger, stats, "Extraction Results")
    
    print("\n✅ Emoji logger test completed!")