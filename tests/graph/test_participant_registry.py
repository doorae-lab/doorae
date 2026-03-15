"""Tests for ParticipantRegistry."""

from doorae.core.profile import AgentProfile
from doorae.graph.participant_registry import ParticipantRegistry


def _make_profile(name: str, *, is_human: bool = False, role: str = "participant") -> AgentProfile:
    return AgentProfile(
        name=name,
        role=role,
        responsibilities=["참여"],
        expertise=["일반"],
        is_human=is_human,
    )


def test_add_and_get_profile() -> None:
    registry = ParticipantRegistry()
    profile = _make_profile("Alice", is_human=True)

    registry.add(profile)

    assert registry.get("Alice") == profile
    assert registry.all_names == ["Alice"]
    assert registry.is_human("Alice") is True


def test_remove_updates_lookup() -> None:
    registry = ParticipantRegistry({"Alice": _make_profile("Alice", is_human=True)})

    registry.remove("Alice")

    assert registry.get("Alice") is None
    assert registry.all_names == []
    assert registry.human_name_lookup == {}


def test_replacing_profile_updates_human_lookup() -> None:
    registry = ParticipantRegistry({"Alice": _make_profile("Alice", is_human=True)})

    registry.add(_make_profile("Alice", is_human=False, role="pm"))

    assert registry.is_human("Alice") is False
    assert registry.human_name_lookup == {}


def test_human_name_lookup_uses_lowercase_keys() -> None:
    registry = ParticipantRegistry(
        {
            "Alice": _make_profile("Alice", is_human=True),
            "PM": _make_profile("PM"),
        }
    )

    assert registry.human_name_lookup == {"alice": "Alice"}
