from itertools import count


class UserRepository:
    """In-memory store. The real one talks to Postgres."""

    def __init__(self) -> None:
        self._rows: dict[int, dict] = {}
        self._ids = count(1)

    def get(self, user_id: int) -> dict | None:
        return self._rows.get(user_id)

    def get_by_email(self, email: str) -> dict | None:
        return next((r for r in self._rows.values() if r["email"] == email), None)

    def add(self, email: str, display_name: str) -> dict:
        row = {"id": next(self._ids), "email": email, "display_name": display_name}
        self._rows[row["id"]] = row
        return row
