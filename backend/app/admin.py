"""Admin CLI (users are never created through the API: ADR-006, RV-G0-006).

    python -m app.admin create-user --login-id taro --display-name "山田 太郎" [--admin]
    python -m app.admin deactivate-user --login-id taro

The password is read from EASF_NEW_USER_PASSWORD or prompted (never passed as an argument).
"""

import argparse
import getpass
import os
import sys

from sqlalchemy import select

from app.auth.models import User
from app.core.config import get_settings
from app.core.db import make_session_factory
from app.core.security import PASSWORD_MAX, PASSWORD_MIN, hash_password


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.admin")
    sub = parser.add_subparsers(dest="command", required=True)
    create = sub.add_parser("create-user")
    create.add_argument("--login-id", required=True)
    create.add_argument("--display-name", required=True)
    create.add_argument("--admin", action="store_true")
    deactivate = sub.add_parser("deactivate-user")
    deactivate.add_argument("--login-id", required=True)
    args = parser.parse_args(argv)

    with make_session_factory(get_settings())() as db:
        existing = db.execute(select(User).where(User.login_id == args.login_id)).scalar_one_or_none()
        if args.command == "create-user":
            if existing is not None:
                print("同じログイン ID の利用者が既にあります。", file=sys.stderr)
                return 1
            password = os.environ.get("EASF_NEW_USER_PASSWORD") or getpass.getpass("パスワード: ")
            if not PASSWORD_MIN <= len(password) <= PASSWORD_MAX:
                print(f"パスワードは {PASSWORD_MIN}〜{PASSWORD_MAX} 文字にしてください。", file=sys.stderr)
                return 1
            db.add(
                User(
                    login_id=args.login_id,
                    display_name=args.display_name,
                    password_hash=hash_password(password),
                    is_admin=args.admin,
                )
            )
            db.commit()
            print("利用者を作成しました。")
            return 0
        if existing is None:
            print("利用者が見つかりません。", file=sys.stderr)
            return 1
        existing.is_active = False
        db.commit()
        print("利用者を無効にしました。")
        return 0


if __name__ == "__main__":
    sys.exit(main())
