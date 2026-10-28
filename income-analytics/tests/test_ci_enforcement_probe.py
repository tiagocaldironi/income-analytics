def test_controlled_ci_enforcement_failure():
    """Temporary remote enforcement probe; never merge into develop."""
    raise AssertionError("Controlled enforcement probe: expected Engineering failure")
