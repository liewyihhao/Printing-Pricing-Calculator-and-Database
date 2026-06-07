from app.models import combo_hash


def test_deterministic():
    a = combo_hash(21, "s1", "p1", "l1", 98)
    b = combo_hash(21, "s1", "p1", "l1", 98)
    assert a == b and len(a) == 64


def test_distinct_inputs_differ():
    base = combo_hash(21, "s1", "p1", "l1", 98)
    assert base != combo_hash(21, "s1", "p1", "l1", 99)   # delivery
    assert base != combo_hash(21, "s2", "p1", "l1", 98)   # size
    assert base != combo_hash(50, "s1", "p1", "l1", 98)   # product


def test_empty_fields_stable():
    assert combo_hash(21, "", "", "", 98) == combo_hash(21, "", "", "", 98)
