import sys

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.user import User


def run(email: str) -> None:
    db = SessionLocal()
    try:
        user = db.execute(
            select(User).where(User.email == email.strip().lower())
        ).scalar_one_or_none()
        if user is None:
            print(f"User not found: {email}")
            sys.exit(1)
        user.is_superuser = True
        user.is_active = True
        db.commit()
        print(f"Promoted {user.email} to superuser")
    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m app.cli.promote <email>")
        sys.exit(1)
    run(sys.argv[1])

def demote(email: str) -> None:
    db = SessionLocal()
    try:
        user = db.execute(
            select(User).where(User.email == email.strip().lower())
        ).scalar_one_or_none()
        if user is None:
            print(f"User not found: {email}")
            sys.exit(1)
        user.is_superuser = False
        db.commit()
        print(f"Demoted {user.email} from superuser")
    finally:
        db.close()