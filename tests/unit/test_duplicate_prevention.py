#!/usr/bin/env python3
"""
Unit Tests for Duplicate Prevention System
Location: tests/unit/test_duplicate_prevention.py

Tests the duplicate detection and prevention functionality.
"""

import unittest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))

from src.utils.duplicate_prevention import (
    DuplicateTracker,
    create_duplicate_tracker,
    filter_duplicate_messages,
    mark_messages_as_processed
)


class TestDuplicateTracker(unittest.TestCase):
    """Test suite for DuplicateTracker"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Create temporary directory for test data
        self.test_dir = Path(tempfile.mkdtemp())
        self.tracker = DuplicateTracker(self.test_dir)
        
        # Sample messages for testing
        self.sample_messages = [
            {
                'id': '1',
                'channel_id': 'test_channel',
                'channel': 'Test Channel',
                'text': 'Hello world',
                'date': datetime.now()
            },
            {
                'id': '2',
                'channel_id': 'test_channel',
                'channel': 'Test Channel',
                'text': 'Different message',
                'date': datetime.now()
            },
            {
                'id': '3',
                'channel_id': 'another_channel',
                'channel': 'Another Channel',
                'text': 'Hello from another channel',
                'date': datetime.now()
            }
        ]
    
    def tearDown(self):
        """Clean up test fixtures"""
        # Close tracker
        self.tracker.close()
        
        # Remove temporary directory
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)
    
    def test_tracker_initialization(self):
        """Test that tracker initializes correctly"""
        self.assertIsNotNone(self.tracker)
        self.assertTrue(self.test_dir.exists())
        self.assertTrue((self.test_dir / "processed_messages.db").exists())
    
    def test_new_message_not_duplicate(self):
        """Test that new messages are not marked as duplicates"""
        message = self.sample_messages[0]
        is_dup, reason = self.tracker.is_duplicate(message)
        
        self.assertFalse(is_dup)
        self.assertEqual(reason, "No duplicate detected")
    
    def test_duplicate_by_message_id(self):
        """Test duplicate detection by message ID"""
        message = self.sample_messages[0]
        
        # First time - not a duplicate
        is_dup, _ = self.tracker.is_duplicate(message)
        self.assertFalse(is_dup)
        
        # Mark as processed
        self.tracker.mark_as_processed(message)
        
        # Second time - should be duplicate
        is_dup, reason = self.tracker.is_duplicate(message)
        self.assertTrue(is_dup)
        self.assertIn("already processed", reason.lower())
    
    def test_duplicate_by_content_hash(self):
        """Test duplicate detection by content hash"""
        # First message
        message1 = self.sample_messages[0]
        self.tracker.mark_as_processed(message1)
        
        # Second message with different ID but same content
        message2 = message1.copy()
        message2['id'] = '999'  # Different ID
        
        is_dup, reason = self.tracker.is_duplicate(message2)
        self.assertTrue(is_dup)
        self.assertIn("identical content", reason.lower())
    
    def test_different_channels_not_duplicate(self):
        """Test that same message ID in different channels is not duplicate"""
        message1 = {
            'id': '1',
            'channel_id': 'channel1',
            'text': 'Test message',
            'date': datetime.now()
        }
        
        message2 = {
            'id': '1',
            'channel_id': 'channel2',
            'text': 'Test message',
            'date': datetime.now()
        }
        
        # Mark first message as processed
        self.tracker.mark_as_processed(message1)
        
        # Second message with same ID but different channel
        # Should be duplicate by content, not by ID
        is_dup, reason = self.tracker.is_duplicate(message2)
        self.assertTrue(is_dup)
        self.assertIn("content", reason.lower())
    
    def test_mark_as_processed(self):
        """Test marking messages as processed"""
        message = self.sample_messages[0]
        
        # Mark as processed
        self.tracker.mark_as_processed(message, status="completed", ai_processed=True)
        
        # Verify it's now marked as duplicate
        is_dup, _ = self.tracker.is_duplicate(message)
        self.assertTrue(is_dup)
    
    def test_filter_duplicates(self):
        """Test filtering duplicates from message list"""
        messages = self.sample_messages.copy()
        
        # Add a duplicate
        duplicate_msg = messages[0].copy()
        messages.append(duplicate_msg)
        
        # Mark first message as processed
        self.tracker.mark_as_processed(messages[0])
        
        # Filter duplicates
        unique_messages = self.tracker.filter_duplicates(messages)
        
        # Should have original count minus the duplicate
        self.assertEqual(len(unique_messages), len(self.sample_messages) - 1)
    
    def test_statistics(self):
        """Test statistics collection"""
        # Process some messages
        for message in self.sample_messages:
            self.tracker.mark_as_processed(message)
        
        # Get statistics
        stats = self.tracker.get_statistics()
        
        self.assertIsNotNone(stats)
        self.assertIn('total_messages_tracked', stats)
        self.assertIn('channels_tracked', stats)
        self.assertIn('content_hashes', stats)
        
        # Verify counts
        self.assertEqual(stats['channels_tracked'], 2)  # test_channel and another_channel
        self.assertGreaterEqual(stats['total_messages_tracked'], 3)
    
    def test_state_persistence(self):
        """Test that state persists across tracker instances"""
        message = self.sample_messages[0]
        
        # Mark message as processed in first tracker
        self.tracker.mark_as_processed(message)
        self.tracker.close()
        
        # Create new tracker with same directory
        new_tracker = DuplicateTracker(self.test_dir)
        
        # Message should still be marked as duplicate
        is_dup, _ = new_tracker.is_duplicate(message)
        self.assertTrue(is_dup)
        
        new_tracker.close()
    
    def test_content_hash_generation(self):
        """Test content hash generation"""
        message1 = {'text': 'Hello World'}
        message2 = {'text': 'hello world'}  # Different case
        message3 = {'text': 'Different content'}
        
        hash1 = self.tracker._generate_content_hash(message1)
        hash2 = self.tracker._generate_content_hash(message2)
        hash3 = self.tracker._generate_content_hash(message3)
        
        # Same content (case-insensitive) should have same hash
        self.assertEqual(hash1, hash2)
        
        # Different content should have different hash
        self.assertNotEqual(hash1, hash3)
    
    def test_empty_message_handling(self):
        """Test handling of messages with no text"""
        message = {
            'id': '1',
            'channel_id': 'test',
            'text': '',
            'date': datetime.now()
        }
        
        # Should not raise an exception
        is_dup, _ = self.tracker.is_duplicate(message)
        self.assertFalse(is_dup)
        
        # Should be able to mark as processed
        self.tracker.mark_as_processed(message)


class TestConvenienceFunctions(unittest.TestCase):
    """Test suite for convenience functions"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.test_dir = Path(tempfile.mkdtemp())
    
    def tearDown(self):
        """Clean up test fixtures"""
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)
    
    def test_create_duplicate_tracker(self):
        """Test tracker creation function"""
        tracker = create_duplicate_tracker(self.test_dir)
        self.assertIsNotNone(tracker)
        self.assertIsInstance(tracker, DuplicateTracker)
        tracker.close()
    
    def test_filter_duplicate_messages(self):
        """Test convenience function for filtering"""
        messages = [
            {'id': '1', 'channel_id': 'test', 'text': 'Message 1', 'date': datetime.now()},
            {'id': '2', 'channel_id': 'test', 'text': 'Message 2', 'date': datetime.now()},
            {'id': '1', 'channel_id': 'test', 'text': 'Message 1', 'date': datetime.now()},  # Duplicate
        ]
        
        tracker = create_duplicate_tracker(self.test_dir)
        
        # Mark first message as processed
        tracker.mark_as_processed(messages[0])
        
        # Filter duplicates
        unique = filter_duplicate_messages(messages, tracker)
        
        # Should have 2 unique messages (excluding the duplicate)
        self.assertEqual(len(unique), 2)
        
        tracker.close()
    
    def test_mark_messages_as_processed(self):
        """Test convenience function for marking multiple messages"""
        messages = [
            {'id': '1', 'channel_id': 'test', 'text': 'Message 1', 'date': datetime.now()},
            {'id': '2', 'channel_id': 'test', 'text': 'Message 2', 'date': datetime.now()},
        ]
        
        tracker = create_duplicate_tracker(self.test_dir)
        
        # Mark all as processed
        mark_messages_as_processed(messages, tracker)
        
        # Verify all are now duplicates
        for message in messages:
            is_dup, _ = tracker.is_duplicate(message)
            self.assertTrue(is_dup)
        
        tracker.close()


def run_tests():
    """Run all tests"""
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test cases
    suite.addTests(loader.loadTestsFromTestCase(TestDuplicateTracker))
    suite.addTests(loader.loadTestsFromTestCase(TestConvenienceFunctions))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Return exit code
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    sys.exit(run_tests())