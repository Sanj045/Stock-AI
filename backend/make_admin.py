from database import SessionLocal
from models import User

db = SessionLocal()

user = (
    db.query(User)
    .filter(User.username == "admin")
    .first()
)

if user:
    user.role = "admin"
    db.commit()
    print("admin is now an admin")
else:
    print("User not found")

db.close()