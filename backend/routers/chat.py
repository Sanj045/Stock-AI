from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from models import User, ChatMessage, Conversation
from schemas import ChatRequest, ChatResponse
from dependencies import get_db, get_current_user

from logger import logger
from stock.context import build_stock_context
from stock.detector import (
    detect_stock_symbol,
    detect_symbol_from_history,
    is_valid_stock_symbol
)
from ai.service import ask_ai, analyze_stock


router = APIRouter(
    tags=["Chat"]
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


@router.post(
    "/conversations/{conversation_id}/chat",
    response_model=ChatResponse
)
def chat(
    conversation_id: int,
    data: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # =====================================================
    # Kiểm tra conversation thuộc user hiện tại
    # =====================================================

    conversation = get_conversation_or_404(
        conversation_id,
        current_user,
        db
    )

    logger.info(
        "User %s sent a message to conversation %s",
        current_user.id,
        conversation_id
    )

    # =====================================================
    # Kiểm tra đây có phải message đầu tiên không
    # =====================================================

    existing_message = (
        db.query(ChatMessage)
        .filter(
            ChatMessage.user_id == current_user.id,
            ChatMessage.conversation_id == conversation_id
        )
        .first()
    )

    # =====================================================
    # Auto-title bằng câu hỏi đầu tiên
    # =====================================================

    if (
        not existing_message
        and conversation.title == "New conversation"
    ):
        conversation.title = (
            data.message
            .strip()[:60]
        )

        db.commit()
        db.refresh(conversation)

        logger.info(
            "Conversation %s auto-title updated",
            conversation_id
        )

    # =====================================================
    # Lấy 5 message gần nhất
    # =====================================================

    recent_messages = (
        db.query(ChatMessage)
        .filter(
            ChatMessage.user_id == current_user.id,
            ChatMessage.conversation_id == conversation_id
        )
        .order_by(
            ChatMessage.id.desc()
        )
        .limit(5)
        .all()
    )

    recent_messages.reverse()

    # =====================================================
    # Tạo history gửi cho Gemini
    # =====================================================

    history = [
        {
            "question": item.question,
            "answer": item.answer
        }
        for item in recent_messages
    ]

    # =====================================================
    # XÁC ĐỊNH MÃ CỔ PHIẾU
    # =====================================================

    symbol = None
    symbol_source = None

    # -----------------------------------------------------
    # 1. Frontend gửi symbol trực tiếp
    # -----------------------------------------------------

    if data.symbol:
        explicit_symbol = (
            data.symbol
            .strip()
            .upper()
        )

        if is_valid_stock_symbol(
            explicit_symbol
        ):
            symbol = explicit_symbol
            symbol_source = "explicit"

        else:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Invalid stock symbol: "
                    f"{explicit_symbol}"
                )
            )

    # -----------------------------------------------------
    # 2. Tự phát hiện ticker từ message hiện tại
    # -----------------------------------------------------

    if symbol is None:
        detected_symbol = detect_stock_symbol(
            data.message
        )

        if detected_symbol:
            symbol = detected_symbol
            symbol_source = "message"

    # -----------------------------------------------------
    # 3. Nếu là câu follow-up không ghi ticker,
    #    tìm ticker trong history
    # -----------------------------------------------------

    if symbol is None:
        history_symbol = detect_symbol_from_history(
            history
        )

        if history_symbol:
            symbol = history_symbol
            symbol_source = "history"

    if symbol:
        logger.info(
            "Resolved stock symbol | "
            "conversation_id=%s | "
            "symbol=%s | "
            "source=%s",
            conversation_id,
            symbol,
            symbol_source
        )

    # =====================================================
    # GỌI AI
    # =====================================================

    try:
        # -------------------------------------------------
        # STOCK-AWARE CHAT
        # -------------------------------------------------

        if symbol:
            logger.info(
                "Stock-aware chat | "
                "user_id=%s | "
                "conversation_id=%s | "
                "symbol=%s",
                current_user.id,
                conversation_id,
                symbol
            )

            stock_context = build_stock_context(
                symbol=symbol,
                news_limit=8
            )

            ai_answer = analyze_stock(
                symbol=symbol,
                stock_context=stock_context,
                question=data.message,
                history=history
            )

        # -------------------------------------------------
        # NORMAL CHAT
        # -------------------------------------------------

        else:
            ai_answer = ask_ai(
                message=data.message,
                history=history
            )

        logger.info(
            "AI response generated for conversation %s",
            conversation_id
        )

    except RuntimeError as exc:
        logger.error(
            "AI service unavailable for conversation %s: %s",
            conversation_id,
            exc
        )

        raise HTTPException(
            status_code=503,
            detail="AI service is temporarily unavailable"
        )

    except Exception as exc:
        logger.exception(
            "Chat processing failed | "
            "user_id=%s | "
            "conversation_id=%s | "
            "symbol=%s | error=%s",
            current_user.id,
            conversation_id,
            symbol,
            exc
        )

        raise HTTPException(
            status_code=503,
            detail="Unable to process chat request"
        )

    # =====================================================
    # Lưu question + answer vào database
    # =====================================================

    message = ChatMessage(
        user_id=current_user.id,
        conversation_id=conversation_id,
        question=data.message,
        answer=ai_answer
    )

    db.add(message)
    db.commit()
    db.refresh(message)

    logger.info(
        "Chat message %s saved for conversation %s",
        message.id,
        conversation_id
    )

    return message


@router.get(
    "/conversations/{conversation_id}/history",
    response_model=list[ChatResponse]
)
def chat_history(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    get_conversation_or_404(
        conversation_id,
        current_user,
        db
    )

    logger.info(
        "User %s requested history for conversation %s",
        current_user.id,
        conversation_id
    )

    return (
        db.query(ChatMessage)
        .filter(
            ChatMessage.user_id == current_user.id,
            ChatMessage.conversation_id == conversation_id
        )
        .order_by(
            ChatMessage.id.asc()
        )
        .all()
    )


@router.delete(
    "/conversations/{conversation_id}/history"
)
def clear_chat_history(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    get_conversation_or_404(
        conversation_id,
        current_user,
        db
    )

    deleted_count = (
        db.query(ChatMessage)
        .filter(
            ChatMessage.user_id == current_user.id,
            ChatMessage.conversation_id == conversation_id
        )
        .delete()
    )

    db.commit()

    logger.info(
        "User %s cleared %s messages from conversation %s",
        current_user.id,
        deleted_count,
        conversation_id
    )

    return {
        "message": "Conversation history cleared"
    }