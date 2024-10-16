import pytest
from ansible_collections.unbyte.gridscale.plugins.module_utils.version import compare_version


@pytest.mark.parametrize(
    "test_input, expected",
    [
        (("1.0.1", "1.0.0"), True),
        (("1.0.1", "1.0.1"), True),
        (("2", "1"), True),
        (("1.0", "1.0"), True),
        (("1.1.1", "1.2.0"), False),
        (("1", "2"), False),
    ],
)
def test_compare_version(test_input, expected):
    assert compare_version(*test_input) == expected


def test_compare_version_exception():
    with pytest.raises(ValueError):
        compare_version(1, 2)
