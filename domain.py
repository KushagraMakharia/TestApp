USERS = {"1": "Alice", "2": "Bob"}
ITEMS = ["apple", "banana", "cherry"]


def divide(a: int, b: int) -> float:
    if b == 0:
        return 0.0
    return a / b


def get_user(user_id: str) -> str:
    return USERS.get(user_id, "Unknown User")


def get_item(index: int) -> str:
    if 0 <= index < len(ITEMS):
        return ITEMS[index]
    return "Unknown Item"
