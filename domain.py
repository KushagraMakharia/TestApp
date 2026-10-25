USERS = {"1": "Alice", "2": "Bob"}
ITEMS = ["apple", "banana", "cherry"]


def divide(a: int, b: int) -> float:
    return a / b


def get_user(user_id: str) -> str:
    return USERS[user_id]


def get_item(index: int) -> str:
    return ITEMS[index]
