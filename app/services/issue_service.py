from __future__ import annotations

from typing import Iterable, List

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.issue import Issue


async def upsert_many(session: AsyncSession, issues: Iterable[dict]) -> List[Issue]:
    """Bulk upsert Issue rows based on primary key (UUID).

    Currently uses PostgreSQL ON CONFLICT; for other DBs adjust accordingly.
    """
    if not issues:
        return []

    stmt = pg_insert(Issue).values(list(issues))
    # Use hubspot_ticket_id for conflict resolution when present, otherwise primary key.
    index_elements = [Issue.hubspot_ticket_id] if any(
        i.get("hubspot_ticket_id") for i in issues
    ) else [Issue.id]

    update_cols = {c.name: c for c in stmt.excluded if not c.primary_key}
    stmt = stmt.on_conflict_do_update(index_elements=index_elements, set_=update_cols)

    await session.execute(stmt)
    await session.commit()

    # Return all IDs we just upserted
    ids = [row["id"] for row in issues]
    q = await session.execute(
        Issue.select().where(Issue.id.in_(ids))  # type: ignore[attr-defined]
    )
    return q.scalars().all() 