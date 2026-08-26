# Database Migrations

Migration `20260826_01` creates synthetic customers and conversations. Migration `20260826_02` adds
plan snapshots, persisted messages, and typed plan-evidence links for grounded current-plan answers.
Apply all forward migrations with:

```bash
DATABASE_URL=postgresql+psycopg://... uv run alembic upgrade head
```
