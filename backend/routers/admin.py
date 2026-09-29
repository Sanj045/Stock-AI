from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from models import User
from schemas import UserResponse, UserRoleUpdate
from dependencies import get_db, require_admin


router = APIRouter(
    prefix="/admin",
    tags=["Admin"]
)


@router.get("/users", response_model=list[UserResponse])
def get_all_users(
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    return db.query(User).all()


@router.patch("/users/{user_id}/role", response_model=UserResponse)
def update_user_role(
    user_id: int,
    data: UserRoleUpdate,
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    user = (
        db.query(User)
        .filter(User.id == user_id)
        .first()
    )

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    user.role = data.role

    db.commit()
    db.refresh(user)

    return user


@router.delete("/users/{user_id}")
def delete_user(
    user_id: int,
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    if admin_user.id == user_id:
        raise HTTPException(
            status_code=400,
            detail="Admin cannot delete own account"
        )

    user = (
        db.query(User)
        .filter(User.id == user_id)
        .first()
    )

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    db.delete(user)
    db.commit()

    return {
        "message": "User deleted"
    }