"""A tiny user repository with a read-through cache."""


class UserRepo:
    def __init__(self):
        # Pretend this is a database table.
        self._db = {}
        # key -> last read result
        self._cache = {}

    def add_user(self, user_id, name):
        self._db[user_id] = {"id": user_id, "name": name}

    def get_user(self, user_id):
        """Return the user record, caching the result for next time."""
        if user_id in self._cache:
            return self._cache[user_id]
        record = self._db.get(user_id)
        # cache a copy so callers can't mutate our backing store
        cached = dict(record) if record is not None else None
        self._cache[user_id] = cached
        return cached

    def update_name(self, user_id, new_name):
        """Rename a user."""
        self._db[user_id]["name"] = new_name

    def delete_user(self, user_id):
        self._db.pop(user_id, None)
        self._cache.pop(user_id, None)
