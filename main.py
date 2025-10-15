#!/usr/bin/env python3
"""
Telegram Knowledge Base Extractor - Main Entry Point

Production-grade async pipeline for automated AI summarization of Telegram
channels with zero duplicate processing.

Features:
- Async message extraction from Telegram channels
- Multi-layer duplicate prevention
- Smart AI routing (Claude + local models)
- Automatic crash recovery
- Comprehensive statistics and monitoring

Usage:
    python main.py
"""

import asyncio
import sys
import signal
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from src.config import get_config, print_config_summary
from src.utils.db_manager import db_manager
from src.utils.duplicate_prevention import create_duplicate_tracker
from src.utils.emoji_logger import create_emoji_logger, log_section, log_stats


logger = create_emoji_logger(__name__)


class TelegramKnowledgeExtractorApp:
    """
    Main application class for Telegram Knowledge Base Extractor
    
    Coordinates all components:
    - Telegram message extraction
    - Duplicate prevention
    - AI processing
    - Data storage and export
    """
    
    def __init__(self):
        """Initialize application"""
        self.config = None
        self.tracker = None
        self.extractor = None
        self.running = False
        self.total_messages_processed = 0
        self.start_time = None
    
    def setup_signal_handlers(self):
        """Setup graceful shutdown handlers"""
        def signal_handler(signum, frame):
            logger.warning("Received interrupt signal, shutting down gracefully...")
            self.running = False
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    def setup_environment(self):
        """Setup application environment"""
        logger.info("Setting up environment...")
        
        # Load configuration
        try:
            self.config = get_config()
            logger.info("✅ Configuration loaded successfully")
        except Exception as e:
            logger.error(f"❌ Failed to load configuration: {e}")
            logger.error("Make sure you have created .env file from .env.template")
            sys.exit(1)
        
        # Create data directories
        data_dir = Path(self.config.storage.data_directory)
        data_dir.mkdir(parents=True, exist_ok=True)
        (data_dir / "exports").mkdir(exist_ok=True)
        
        # Create logs directory
        log_dir = Path(self.config.logging.log_file).parent
        log_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info("✅ Directories created")
    
    def setup_databases(self):
        """Setup centralized database management"""
        logger.info("Setting up database connections...")
        
        data_dir = Path(self.config.storage.data_directory)
        
        # Register databases with centralized manager
        db_manager.register_database(
            "duplicate_tracker",
            data_dir / "processed_messages.db"
        )
        
        logger.info("✅ Database connections configured")
        
        # Get connection stats
        stats = db_manager.get_stats()
        logger.debug(f"Database stats: {stats}")
    
    def initialize_components(self):
        """Initialize all application components"""
        logger.info("Initializing components...")
        
        # Initialize duplicate tracker
        data_dir = Path(self.config.storage.data_directory)
        self.tracker = create_duplicate_tracker(data_dir)
        logger.info("✅ Duplicate tracker initialized")
        
        # Note: Actual Telegram extractor would be initialized here
        # For this demo, we'll show the structure
        logger.info("✅ All components initialized")
    
    def simulate_message_extraction(self, channel: str, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Simulate message extraction (for demo purposes)
        
        In production, this would use the actual TelegramKnowledgeExtractor
        
        Args:
            channel: Channel name
            limit: Number of messages to extract
            
        Returns:
            List of simulated messages
        """
        logger.info(f"📡 Extracting messages from {channel}...")
        
        # Simulate some messages
        messages = []
        for i in range(1, limit + 1):
            message = {
                'id': str(i),
                'channel_id': channel,
                'channel': channel,
                'text': f'Sample message {i} from {channel}',
                'date': datetime.now()
            }
            messages.append(message)
        
        # Add some duplicates for testing
        if limit > 5:
            messages.append(messages[0])  # Duplicate by ID
            messages.append({
                'id': str(limit + 1),
                'channel_id': channel,
                'channel': channel,
                'text': messages[0]['text'],  # Duplicate by content
                'date': datetime.now()
            })
        
        logger.info(f"✅ Extracted {len(messages)} messages")
        return messages
    
    def process_channel(self, channel: str) -> Dict[str, Any]:
        """
        Process a single channel
        
        Args:
            channel: Channel name
            
        Returns:
            Dictionary with processing statistics
        """
        logger.info(f"\n📡 Processing channel: {channel}")
        
        # Extract messages (simulated for demo)
        messages = self.simulate_message_extraction(
            channel,
            limit=self.config.processing.message_limit_per_channel
        )
        
        # Filter duplicates
        new_messages = []
        duplicate_count = 0
        
        for message in messages:
            is_dup, reason = self.tracker.is_duplicate(message)
            if is_dup:
                duplicate_count += 1
                logger.debug(f"Skipping duplicate: {message['id']} - {reason}")
            else:
                new_messages.append(message)
                self.tracker.mark_as_processed(message)
        
        # Statistics
        stats = {
            'channel': channel,
            'total_messages': len(messages),
            'new_messages': len(new_messages),
            'duplicates': duplicate_count,
            'duplicate_rate': f"{(duplicate_count / len(messages) * 100):.1f}%" if messages else "0%"
        }
        
        logger.info(f"   📊 Total: {stats['total_messages']} | "
                   f"New: {stats['new_messages']} | "
                   f"Duplicates: {stats['duplicates']} ({stats['duplicate_rate']})")
        
        self.total_messages_processed += len(new_messages)
        return stats
    
    async def run(self):
        """Main application execution"""
        self.running = True
        self.start_time = datetime.now()
        
        try:
            # Display banner
            log_section(logger, "Telegram Knowledge Base Extractor")
            print_config_summary(self.config)
            
            # Setup
            logger.info("\n🚀 Starting application...")
            self.setup_environment()
            self.setup_databases()
            self.initialize_components()
            
            # Process channels
            log_section(logger, "Processing Channels")
            
            channel_stats = []
            for channel in self.config.telegram.channels:
                if not self.running:
                    logger.warning("Interrupted, stopping...")
                    break
                
                stats = self.process_channel(channel)
                channel_stats.append(stats)
                
                # Small delay between channels
                await asyncio.sleep(1)
            
            # Final statistics
            self.display_final_statistics(channel_stats)
            
        except Exception as e:
            logger.error(f"❌ Application error: {e}", exc_info=True)
            raise
        
        finally:
            await self.cleanup()
    
    def display_final_statistics(self, channel_stats: List[Dict]):
        """Display final processing statistics"""
        log_section(logger, "Extraction Complete")
        
        # Aggregate statistics
        total_extracted = sum(s['total_messages'] for s in channel_stats)
        total_new = sum(s['new_messages'] for s in channel_stats)
        total_duplicates = sum(s['duplicates'] for s in channel_stats)
        
        # Calculate processing time
        if self.start_time:
            elapsed = (datetime.now() - self.start_time).total_seconds()
            processing_time = f"{elapsed:.2f}s"
            messages_per_second = total_new / elapsed if elapsed > 0 else 0
        else:
            processing_time = "N/A"
            messages_per_second = 0
        
        # Display results
        results = {
            'Channels Processed': len(channel_stats),
            'Total Messages Extracted': total_extracted,
            'New Messages': total_new,
            'Duplicates Filtered': total_duplicates,
            'Duplicate Rate': f"{(total_duplicates / total_extracted * 100):.1f}%" if total_extracted > 0 else "0%",
            'Processing Time': processing_time,
            'Throughput': f"{messages_per_second:.2f} msg/s"
        }
        
        log_stats(logger, results, "Final Results")
        
        # Duplicate tracker statistics
        tracker_stats = self.tracker.get_statistics()
        tracker_summary = {
            'Total Tracked': tracker_stats['total_messages_tracked'],
            'Channels': tracker_stats['channels_tracked'],
            'Content Hashes': tracker_stats['content_hashes'],
            'Session Duplicates': tracker_stats['session_stats']['duplicates_detected']
        }
        
        log_stats(logger, tracker_summary, "Duplicate Prevention Stats")
        
        # Success message
        logger.info("\n🎉 Extraction workflow completed successfully!")
        logger.info(f"💾 Data saved to: {self.config.storage.data_directory}")
    
    async def cleanup(self):
        """Cleanup resources"""
        logger.info("\n🧹 Cleaning up resources...")
        
        try:
            # Close duplicate tracker
            if self.tracker:
                self.tracker.close()
                logger.info("✅ Duplicate tracker closed")
            
            # Close database connections
            db_manager.close_all_connections()
            logger.info("✅ Database connections closed")
            
            logger.info("✅ Cleanup completed")
            
        except Exception as e:
            logger.error(f"❌ Cleanup error: {e}")


async def main():
    """
    Main entry point
    
    Creates and runs the application instance
    """
    app = TelegramKnowledgeExtractorApp()
    app.setup_signal_handlers()
    
    try:
        await app.run()
    except KeyboardInterrupt:
        logger.info("\n⚠️  Interrupted by user")
    except Exception as e:
        logger.error(f"\n❌ Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    # Run the async application
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 Goodbye!")
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        sys.exit(1)