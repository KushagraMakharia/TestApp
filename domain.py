USERS = {"1": "Alice", "2": "Bob"}
ITEMS = ["apple", "banana", "cherry"]


def divide(a: int, b: int) -> float:
    return a / b


def get_user(user_id: str) -> str:
    return USERS.get(str(user_id), "Unknown User")


def get_item(index: int) -> str:
    if not isinstance(index, int):
        try:
            index = int(index)
        except (TypeError, ValueError):
            return "Unknown Item"

    if 0 <= index < len(ITEMS):
        return ITEMS[index]
    return "Unknown Item"
