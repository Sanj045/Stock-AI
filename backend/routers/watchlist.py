from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from models import User, Watchlist
from schemas import WatchlistCreate, WatchlistResponse
from dependencies import get_db, get_current_user


router = APIRouter(
    tags=["Watchlist"]
)


@router.post("/watchlist", response_model=WatchlistResponse)
def add_watchlist(
    data: WatchlistCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    symbol = data.symbol

    existing = (
        db.query(Watchlist)
        .filter(
            Watchlist.user_id == current_user.id,
            Watchlist.symbol == symbol
        )
        .first()
    )

    if existing:
        raise HTTPException(
            status_code=400,
            detail="Symbol already exists in watchlist"
        )

    item = Watchlist(
        user_id=current_user.id,
        symbol=symbol
    )

    db.add(item)
    db.commit()
    db.refresh(item)

    return item


@router.get("/watchlist", response_model=list[WatchlistResponse])
def get_watchlist(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return (
        db.query(Watchlist)
        .filter(Watchlist.user_id == current_user.id)
        .all()
    )


@router.delete("/watchlist/{symbol}")
def delete_watchlist(
    symbol: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    symbol = symbol.upper()

    item = (
        db.query(Watchlist)
        .filter(
            Watchlist.user_id == current_user.id,
            Watchlist.symbol == symbol
        )
        .first()
    )

    if not item:
        raise HTTPException(
            status_code=404,
            detail="Symbol not found"
        )

    db.delete(item)
    db.commit()

    return {
        "message": f"{symbol} removed from watchlist"
    }