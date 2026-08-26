# Database Migrations

The initial migration creates only the `synthetic_customers` and `conversations` tables required by
the approved conversation-creation feature. Apply migrations with:

```bash
DATABASE_URL=postgresql+psycopg://... uv run alembic upgrade head
```
