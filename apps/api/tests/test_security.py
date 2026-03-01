from app.core.security import is_well_formed_pat


def test_pat_format_accepts_expected_prefix_and_length() -> None:
    assert is_well_formed_pat("xic_pat_abcDEF123_-abcdefghijklmnopqrst")


def test_pat_format_rejects_bad_shapes() -> None:
    assert not is_well_formed_pat("")
    assert not is_well_formed_pat("abc_pat_foo")
    assert not is_well_formed_pat("xic_pat_short")
