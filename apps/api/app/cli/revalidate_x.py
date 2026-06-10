from __future__ import annotations

import json

from sqlalchemy import select

from app.db.models import User, XIntegration
from app.db.session import SessionLocal
from app.services.x_api import get_x_client
from app.services.x_ingestion import revalidate_user_sources


def main() -> None:
    totals = {"verified": 0, "updated": 0, "unavailable": 0}
    with SessionLocal() as db:
        rows = db.execute(select(User, XIntegration).join(XIntegration, XIntegration.user_id == User.id)).all()
        for user, integration in rows:
            result = revalidate_user_sources(
                db=db,
                user=user,
                client=get_x_client(db=db, user_id=user.id, integration=integration),
            )
            for key, value in result.items():
                totals[key] += value
    print(json.dumps(totals, sort_keys=True))


if __name__ == "__main__":
    main()
