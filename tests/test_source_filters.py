import pytest

from pdm._types import RepositoryConfig
from pdm.utils import filtered_sources


@pytest.mark.parametrize(
    "pattern, package, expected",
    [
        ("pkg[!a]", "pkga", ["private", "public"]),
        ("pkg[!a]", "pkgb", ["private"]),
        ("pkg[a]", "pkga", ["private"]),
        ("pkg[a]", "pkgb", ["private", "public"]),
    ],
)
def test_include_packages_character_class(pattern: str, package: str, expected: list[str]) -> None:
    private = RepositoryConfig("pypi", "private", url="https://example.invalid/simple", include_packages=[pattern])
    public = RepositoryConfig("pypi", "public", url="https://public.invalid/simple")

    assert [source.name for source in filtered_sources([private, public], package)] == expected


@pytest.mark.parametrize(
    "pattern, package, expected",
    [
        ("pkg[!a]", "pkga", ["private", "public"]),
        ("pkg[!a]", "pkgb", ["public"]),
        ("pkg[a]", "pkga", ["public"]),
        ("pkg[a]", "pkgb", ["private", "public"]),
    ],
)
def test_exclude_packages_character_class(pattern: str, package: str, expected: list[str]) -> None:
    private = RepositoryConfig("pypi", "private", url="https://example.invalid/simple", exclude_packages=[pattern])
    public = RepositoryConfig("pypi", "public", url="https://public.invalid/simple")

    assert [source.name for source in filtered_sources([private, public], package)] == expected
