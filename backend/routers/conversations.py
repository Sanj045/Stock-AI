from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from models import User, Conversation
from dependencies import get_db, get_current_user

from schemas import (
    ConversationCreate,
    ConversationUpdate,
    ConversationResponse
)


router = APIRouter(
    prefix="/conversations",
    tags=["Conversations"]
)


def get_conversation_or_404(
    conversation_id: int,
    current_user: User,
    db: Session
):
    conversation = (
        db.query(Conversation)
        .filter(
            Conversation.id == conversation_id,
            Conversation.user_id == current_user.id
        )
        .first()
    )

    if not conversation:
        raise HTTPException(
            status_code=404,
            detail="Conversation not found"
        )

    return conversation


@router.post("", response_model=ConversationResponse)
def create_conversation(
    data: ConversationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    conversation = Conversation(
        user_id=current_user.id,
        title=data.title.strip()
    )

    db.add(conversation)
    db.commit()
    db.refresh(conversation)

    return conversation


@router.get("", response_model=list[ConversationResponse])
def get_conversations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return (
        db.query(Conversation)
        .filter(
            Conversation.user_id == current_user.id
        )
        .order_by(Conversation.id.desc())
        .all()
    )


@router.get(
    "/{conversation_id}",
    response_model=ConversationResponse
)
def get_conversation(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return get_conversation_or_404(
        conversation_id,
        current_user,
        db
    )


@router.patch(
    "/{conversation_id}",
    response_model=ConversationResponse
)
def update_conversation(
    conversation_id: int,
    data: ConversationUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    conversation = get_conversation_or_404(
        conversation_id,
        current_user,
        db
    )

    conversation.title = data.title.strip()

    db.commit()
    db.refresh(conversation)

    return conversation


@router.delete("/{conversation_id}")
def delete_conversation(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    conversation = get_conversation_or_404(
        conversation_id,
        current_user,
        db
    )

    db.delete(conversation)
    db.commit()

    return {
        "message": "Conversation deleted"
    }