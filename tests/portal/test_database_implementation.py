"""
Database Implementation Test

Quick test to verify database implementation works correctly.

Usage:
    python utils/tests/test_database_implementation.py
"""

import sys
import os
import tempfile
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

def test_database_basic_operations():
    """Test basic database operations: create conversation, save messages."""
    
    print("\n" + "="*70)
    print("TESTING DATABASE IMPLEMENTATION")
    print("="*70 + "\n")
    
    # Override DATABASE_URL to use a temp SQLite database
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        temp_db_path = tmp.name
    
    os.environ["DATABASE_URL"] = f"sqlite:///{temp_db_path}"
    os.environ["DATABASE_TYPE"] = "sqlite"
    
    try:
        from database import db
        from database.exceptions import ConversationNotFoundError
        
        # Test 1: Initialize database
        print("✓ Test 1: Initializing database...")
        db.initialize(debug=False)
        assert db.is_initialized(), "Database should be initialized"
        print("  ✅ Database initialized successfully\n")
        
        # Test 2: Create conversation
        print("✓ Test 2: Creating conversation...")
        conv = db.create_conversation(
            user_id="user_001",
            title="Test Conversation"
        )
        assert conv["id"], "Conversation should have an ID"
        assert conv["user_id"] == "user_001", "User ID should match"
        assert conv["status"] == "ACTIVE", "Status should be ACTIVE"
        assert conv["message_count"] == 0, "Initial message count should be 0"
        conversation_id = conv["id"]
        print(f"  ✅ Created conversation: {conversation_id}\n")
        
        # Test 3: Save user message
        print("✓ Test 3: Saving user message...")
        msg = db.save_user_message(
            conversation_id=conversation_id,
            content="Hello, how can you help me?",
            request_id="req_001"
        )
        assert msg["id"], "Message should have an ID"
        assert msg["role"] == "user", "Role should be 'user'"
        assert msg["content"] == "Hello, how can you help me?", "Content should match"
        assert msg["request_id"] == "req_001", "Request ID should match"
        print(f"  ✅ Saved user message: {msg['id']}\n")
        
        # Test 4: Save assistant message
        print("✓ Test 4: Saving assistant message...")
        msg = db.save_assistant_message(
            conversation_id=conversation_id,
            content="I can help you with many things!",
            request_id="req_001",
            metadata={
                "tokens": 150,
                "model_name": "llama3.2:3b",
                "latency_ms": 2500
            }
        )
        assert msg["id"], "Message should have an ID"
        assert msg["role"] == "assistant", "Role should be 'assistant'"
        assert msg["tokens"] == 150, "Tokens should match"
        print(f"  ✅ Saved assistant message: {msg['id']}\n")
        
        # Test 5: Get conversation and verify message count updated
        print("✓ Test 5: Verifying conversation metadata updated...")
        conv = db.get_conversation(conversation_id)
        assert conv["message_count"] == 2, f"Message count should be 2, got {conv['message_count']}"
        assert conv["last_message_at"], "last_message_at should be set"
        print(f"  ✅ Conversation updated: message_count={conv['message_count']}\n")
        
        # Test 6: Get messages
        print("✓ Test 6: Fetching messages...")
        messages = db.get_messages(conversation_id, limit=10)
        assert len(messages) == 2, f"Should have 2 messages, got {len(messages)}"
        assert messages[0]["role"] == "user", "First message should be from user"
        assert messages[1]["role"] == "assistant", "Second message should be from assistant"
        print(f"  ✅ Fetched {len(messages)} messages\n")
        
        # Test 7: Get last N messages
        print("✓ Test 7: Fetching last N messages...")
        last_messages = db.get_last_n_messages(conversation_id, n=5)
        assert len(last_messages) == 2, "Should return last 2 messages"
        print(f"  ✅ Fetched last {len(last_messages)} messages\n")
        
        # Test 8: List conversations
        print("✓ Test 8: Listing conversations...")
        convs = db.list_conversations(user_id="user_001", limit=10)
        assert len(convs) >= 1, "Should have at least 1 conversation"
        print(f"  ✅ Listed {len(convs)} conversation(s)\n")
        
        # Test 9: Archive conversation
        print("✓ Test 9: Archiving conversation...")
        archived = db.archive_conversation(conversation_id)
        assert archived["status"] == "ARCHIVED", "Status should be ARCHIVED"
        assert archived["archived_at"], "archived_at should be set"
        print(f"  ✅ Archived conversation\n")
        
        # Test 10: Verify archived conversation not in active list
        print("✓ Test 10: Verifying archived conversation not in active list...")
        convs = db.list_conversations(user_id="user_001", include_archived=False)
        assert conversation_id not in [c["id"] for c in convs], "Archived conversation should not be in active list"
        print(f"  ✅ Archived conversation correctly hidden\n")
        
        # Test 11: Get archived conversation when including archived
        print("✓ Test 11: Getting archived conversation when including archived...")
        convs = db.list_conversations(user_id="user_001", include_archived=True)
        assert conversation_id in [c["id"] for c in convs], "Should find archived conversation when including archived"
        print(f"  ✅ Archived conversation found when including archived\n")
        
        # Test 12: Error handling - invalid conversation
        print("✓ Test 12: Testing error handling...")
        try:
            db.save_user_message(
                conversation_id="invalid_id",
                content="test",
                request_id="req_test"
            )
            print("  ❌ Should have raised ConversationNotFoundError")
            return False
        except ConversationNotFoundError:
            print("  ✅ Correctly raised ConversationNotFoundError\n")
        
        # Test 13: Database shutdown
        print("✓ Test 13: Shutting down database...")
        db.shutdown()
        assert not db.is_initialized(), "Database should be shut down"
        print("  ✅ Database shut down successfully\n")
        
        print("="*70)
        print("✅ ALL TESTS PASSED!")
        print("="*70 + "\n")
        return True
    
    except AssertionError as e:
        print(f"\n❌ ASSERTION FAILED: {str(e)}\n")
        return False
    
    except Exception as e:
        print(f"\n❌ TEST FAILED: {str(e)}\n")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # Cleanup
        if os.path.exists(temp_db_path):
            try:
                os.remove(temp_db_path)
            except:
                pass


if __name__ == "__main__":
    success = test_database_basic_operations()
    sys.exit(0 if success else 1)
