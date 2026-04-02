import argparse
import sys
from pathlib import Path
from getpass import getpass

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app import app, db, User


CONFIRM_PHRASE = "MAKE_USER_ADMIN"


def _normalize_email(raw: str) -> str:
    return (raw or "").strip().lower()


def promote_user_to_admin(email: str, force: bool = False) -> int:
    email = _normalize_email(email)
    if not email:
        print("ERROR: email is required.")
        return 2

    with app.app_context():
        target_user = User.query.filter_by(email=email).first()
        if not target_user:
            print(f"ERROR: user not found for email={email}")
            return 3

        if target_user.role == "admin":
            print(f"INFO: user is already admin -> id={target_user.id}, email={target_user.email}")
            return 0

        admin_count = User.query.filter_by(role="admin").count()
        if admin_count > 0 and not force:
            print(
                "ERROR: at least one admin already exists. "
                "Use admin panel (/admin/users) for role changes. "
                "If you really need this script, run with --force."
            )
            return 4

        typed = getpass(f"Type confirmation phrase '{CONFIRM_PHRASE}' to continue: ")
        if typed != CONFIRM_PHRASE:
            print("ERROR: confirmation phrase mismatch. Aborted.")
            return 5

        old_role = target_user.role
        target_user.role = "admin"
        try:
            db.session.commit()
        except Exception as exc:
            db.session.rollback()
            print(f"ERROR: database commit failed: {exc}")
            return 6

        print(
            "OK: role updated "
            f"user_id={target_user.id} email={target_user.email} {old_role}->admin"
        )
        return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Bootstrap first admin safely. "
            "If an admin already exists, use /admin/users in the panel instead."
        )
    )
    parser.add_argument("--email", required=True, help="Target user email")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Allow promotion even when an admin already exists (emergency only).",
    )

    args = parser.parse_args()
    return promote_user_to_admin(args.email, force=args.force)


if __name__ == "__main__":
    sys.exit(main())
