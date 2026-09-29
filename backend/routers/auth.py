from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from dependencies import get_db
from models import User
from schemas import UserCreate, UserResponse, Token
from logger import logger

from auth import (
    hash_password,
    verify_password,
    create_access_token
)


router = APIRouter(
    tags=["Authentication"]
)


@router.post("/register", response_model=UserResponse)
def register(
    user_data: UserCreate,
    db: Session = Depends(get_db)
):
    username = user_data.username.strip().lower()

    existing_user = (
        db.query(User)
        .filter(User.username == username)
        .first()
    )

    if existing_user:
        logger.warning(
            "Registration failed because username already exists: %s",
            username
        )

        raise HTTPException(
            status_code=400,
            detail="Username already exists"
        )

    new_user = User(
        username=username,
        password_hash=hash_password(user_data.password),
        role="user"
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    logger.info(
        "New user registered: %s",
        new_user.username
    )

    return new_user


@router.post("/login", response_model=Token)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    username = form_data.username.strip().lower()

    user = (
        db.query(User)
        .filter(User.username == username)
        .first()
    )

    if not user:
        logger.warning(
            "Failed login attempt for username: %s",
            username
        )

        raise HTTPException(
            status_code=401,
            detail="Invalid username or password"
        )

    if not verify_password(
        form_data.password,
        user.password_hash
    ):
        logger.warning(
            "Failed login attempt for username: %s",
            username
        )

        raise HTTPException(
            status_code=401,
            detail="Invalid username or password"
        )

    access_token = create_access_token(
        data={
            "sub": str(user.id),
            "username": user.username
        }
    )

    logger.info(
        "User logged in: %s",
        user.username
    )

    return {
        "access_token": access_token,
        "token_type": "bearer"
    }