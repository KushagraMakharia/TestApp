from app import divide, get_user, get_item


def test_divide_success():
    assert divide(10, 2) == 5.0


def test_divide_by_zero():
    # Expected behavior: return 0.0 when dividing by zero to avoid crash
    assert divide(10, 0) == 0.0


def test_get_user_success():
    assert get_user("1") == "Alice"


def test_get_user_failure():
    # Expected behavior: return "Unknown User" for non-existent users
    assert get_user("999") == "Unknown User"


def test_get_item_success():
    assert get_item(1) == "banana"


def test_get_item_failure():
    # Expected behavior: return "Unknown Item" for out-of-bound indices
    assert get_item(999) == "Unknown Item"
