from src.db import add_bot, list_bots, update_bot_status, delete_bot


class BotRegistry:
    """Generic multi-bot registry backed by SQLite."""

    def register(self, name: str, bot_type: str = "generic", description: str = ""):
        """Register a new bot."""
        add_bot(name, bot_type, description)

    def all_bots(self):
        """Return all bots."""
        return list_bots()

    def set_status(self, bot_id: int, status: str):
        """Update a bot's status."""
        update_bot_status(bot_id, status)

    def remove(self, bot_id: int):
        """Remove a bot from the registry."""
        delete_bot(bot_id)
