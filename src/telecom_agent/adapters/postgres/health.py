from sqlalchemy import Engine, text
from sqlalchemy.exc import SQLAlchemyError


class SqlAlchemyDatabaseHealth:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def is_healthy(self) -> bool:
        try:
            with self._engine.connect() as connection:
                connection.execute(text("SELECT 1"))
        except SQLAlchemyError:
            return False
        return True
