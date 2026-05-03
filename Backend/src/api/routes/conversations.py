import logging
import uuid
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from src.db.supabase import supabase_client
from src.api.auth import get_current_user, UserResponse

router = APIRouter(prefix="/conversations", tags=["conversations"])
logger = logging.getLogger(__name__)


class ConversationCreate(BaseModel):
    title: Optional[str] = None


class ConversationResponse(BaseModel):
    id: str
    user_id: str
    title: Optional[str]
    created_at: str
    last_message_at: str


@router.post("", response_model=ConversationResponse)
async def create_conversation(
    conversation: ConversationCreate,
    current_user: UserResponse = Depends(get_current_user),
):
    """Create a new conversation for the authenticated user."""
    conversation_id = str(uuid.uuid4())
    
    title = conversation.title or f"Conversation {conversation_id[:8]}"
    
    try:
        await supabase_client.execute(
            '''
            INSERT INTO conversations (id, user_id, title, created_at, last_message_at)
            VALUES ($1, $2, $3, now(), now())
            ''',
            conversation_id,
            current_user.id,
            title,
        )
        
        row = await supabase_client.fetchrow(
            'SELECT id, user_id, title, created_at, last_message_at FROM conversations WHERE id = $1',
            conversation_id,
        )
        
        return ConversationResponse(
            id=str(row["id"]),
            user_id=str(row["user_id"]),
            title=row["title"],
            created_at=str(row["created_at"]),
            last_message_at=str(row["last_message_at"]),
        )
    except Exception as e:
        logger.error(f"Failed to create conversation: {e}")
        raise HTTPException(status_code=500, detail="Failed to create conversation")


@router.get("", response_model=list[ConversationResponse])
async def list_conversations(
    current_user: UserResponse = Depends(get_current_user),
):
    """List all conversations for the authenticated user."""
    try:
        rows = await supabase_client.fetch(
            '''
            SELECT id, user_id, title, created_at, last_message_at
            FROM conversations
            WHERE user_id = $1
            ORDER BY last_message_at DESC
            ''',
            current_user.id,
        )
        
        return [
            ConversationResponse(
                id=str(row["id"]),
                user_id=str(row["user_id"]),
                title=row["title"],
                created_at=str(row["created_at"]),
                last_message_at=str(row["last_message_at"]),
            )
            for row in rows
        ]
    except Exception as e:
        logger.error(f"Failed to list conversations: {e}")
        raise HTTPException(status_code=500, detail="Failed to list conversations")


@router.get("/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: str,
    current_user: UserResponse = Depends(get_current_user),
):
    """Get a specific conversation."""
    try:
        row = await supabase_client.fetchrow(
            '''
            SELECT id, user_id, title, created_at, last_message_at
            FROM conversations
            WHERE id = $1 AND user_id = $2
            ''',
            conversation_id,
            current_user.id,
        )
        
        if not row:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        return ConversationResponse(
            id=str(row["id"]),
            user_id=str(row["user_id"]),
            title=row["title"],
            created_at=str(row["created_at"]),
            last_message_at=str(row["last_message_at"]),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get conversation: {e}")
        raise HTTPException(status_code=500, detail="Failed to get conversation")


@router.delete("/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    current_user: UserResponse = Depends(get_current_user),
):
    """Delete a conversation and its messages."""
    try:
        result = await supabase_client.execute(
            '''
            DELETE FROM conversations
            WHERE id = $1 AND user_id = $2
            ''',
            conversation_id,
            current_user.id,
        )
        
        if result == 0:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        return {"status": "deleted", "conversation_id": conversation_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete conversation: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete conversation")