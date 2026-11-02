"""AI-assisted preservation controls for source-filter normalization."""

import pytest

from pdm._types import RepositoryConfig
from pdm.utils import filtered_sources


@pytest.mark.parametrize("separator", ["._", "!", "!._!"])
@pytest.mark.parametrize("field", ["include_packages", "exclude_packages"])
def test_punctuation_outside_classes_keeps_separator_normalization(separator: str, field: str) -> None:
    patterns = ["unrelated-*", f"Acme{separator}[A-C]?*"]
    private = RepositoryConfig(
        "pypi",
        "private",
        include_packages=patterns if field == "include_packages" else [],
        exclude_packages=patterns if field == "exclude_packages" else [],
    )
    public = RepositoryConfig("pypi", "public")
    sources = [public, private]

    # Neither pattern contains a negated class. Punctuation outside a class
    # historically collapses to a separator, just as dots and underscores do.
    expected = [private] if field == "include_packages" else [public]
    assert filtered_sources(sources, "ACME__BETA") == expected
    assert filtered_sources(sources, "acme.delta") == sources
    assert filtered_sources(sources, None) == sources
    assert patterns == ["unrelated-*", f"Acme{separator}[A-C]?*"]
    assert sources == [public, private]


def test_multiple_inclusions_keep_order_and_override_exclusions() -> None:
    first = RepositoryConfig(
        "pypi", "first", include_packages=["other", "Acme.[A-C]*"], exclude_packages=["*"]
    )
    public = RepositoryConfig("pypi", "public")
    second = RepositoryConfig("pypi", "second", include_packages=["acme_?eta"])
    excluded = RepositoryConfig("pypi", "excluded", exclude_packages=["acme-*"])
    sources = [second, public, excluded, first]

    result = filtered_sources(sources, "ACME.BETA")
    assert len(result) == 2
    assert result[0] is second
    assert result[1] is first
    assert filtered_sources(sources, "unrelated") == [second, public, excluded]
    assert filtered_sources(sources, None) == sources
    assert sources == [second, public, excluded, first]


def test_empty_filters_and_source_lists() -> None:
    source = RepositoryConfig("pypi", "public", include_packages=[], exclude_packages=[])

    assert filtered_sources([], "acme") == []
    assert filtered_sources([], None) == []
    assert filtered_sources([source], "acme") == [source]
    assert filtered_sources([source], None) == [source]
