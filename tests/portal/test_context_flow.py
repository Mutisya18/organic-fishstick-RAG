#!/usr/bin/env python3
"""
Test script to understand context building flow
"""
import sys
from database import db as database_manager
from database.core.session import get_session
from database.models import Message, Conversation
from utils.context.context_builder import build_rag_context
from sqlalchemy import desc

# Initialize database
print("[TEST] Initializing database...")
database_manager.initialize(debug=False)

# Get last conversation
print("[TEST] Querying last conversation...")
with get_session() as session:
    last_conv = session.query(Conversation).order_by(desc(Conversation.created_at)).first()
    
    if not last_conv:
        print("[TEST] No conversations found!")
        sys.exit(1)
    
    conversation_id = last_conv.id
    print(f"[TEST] Found conversation: {conversation_id}")
    print(f"[TEST] Conversation metadata says: {last_conv.message_count} messages")
    
    # Show all messages in this conversation
    all_messages = (
        session.query(Message)
        .filter(Message.conversation_id == conversation_id)
        .order_by(Message.created_at)
        .all()
    )
    
    print(f"[TEST] Database has {len(all_messages)} messages in this conversation")
    print("\n[TEST] All messages in conversation:")
    for i, msg in enumerate(all_messages, 1):
        role = msg.role.value if hasattr(msg.role, 'value') else str(msg.role)
        print(f"  {i}. [{role}] {msg.content[:60]}...")
    
    print("\n[TEST] Now testing context_builder.build_rag_context()...")
    
    # Call context builder like the app does
    context_result = build_rag_context(
        conversation_id=conversation_id,
        user_message="test message",
        db_manager=database_manager,
        prompt_version="1.0.0"
    )
    
    print(f"\n[TEST] Context builder returned:")
    print(f"  - system_prompt length: {len(context_result.get('system_prompt', ''))}")
    print(f"  - context length: {len(context_result.get('context', ''))}")
    print(f"  - user_message: {context_result.get('user_message', '')}")
    
    print(f"\n[TEST] Full context string:")
    print("-" * 80)
    print(context_result.get('context', '[EMPTY]'))
    print("-" * 80)
    
    # Count messages in context
    context_str = context_result.get('context', '')
    message_count = context_str.count('\n') + (1 if context_str else 0)
    print(f"\n[TEST] Context appears to have {message_count} messages")
    print(f"[TEST] Context string length: {len(context_str)} chars")
