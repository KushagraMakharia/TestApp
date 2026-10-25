USERS = {"1": "Alice", "2": "Bob"}
ITEMS = ["apple", "banana", "cherry"]


def divide(a: int, b: int) -> float:
    return a / b


def get_user(user_id: str) -> str:
    return USERS.get(user_id, "Unknown User")


def get_item(index: int) -> str:
    return ITEMS[index]
