"""Dynamic participant registry shared across workflow components."""

from __future__ import annotations

from collections.abc import Mapping

from doorae.core.profile import AgentProfile


class ParticipantRegistry:
    """Runtime registry for active top-level meeting participants."""

    def __init__(self, profiles: Mapping[str, AgentProfile] | None = None) -> None:
        self._profiles: dict[str, AgentProfile] = {}
        self._human_name_lookup: dict[str, str] = {}

        for profile in (profiles or {}).values():
            self.add(profile)

    def add(self, profile: AgentProfile) -> None:
        previous = self._profiles.get(profile.name)
        if previous is not None and previous.is_human:
            self._human_name_lookup.pop(previous.name.lower(), None)

        self._profiles[profile.name] = profile
        if profile.is_human:
            self._human_name_lookup[profile.name.lower()] = profile.name

    def remove(self, name: str) -> None:
        profile = self._profiles.pop(name, None)
        if profile is not None and profile.is_human:
            self._human_name_lookup.pop(profile.name.lower(), None)

    def get(self, name: str) -> AgentProfile | None:
        return self._profiles.get(name)

    def is_human(self, name: str) -> bool:
        profile = self.get(name)
        return bool(profile is not None and profile.is_human)

    @property
    def all_names(self) -> list[str]:
        return list(self._profiles.keys())

    @property
    def human_name_lookup(self) -> dict[str, str]:
        return dict(self._human_name_lookup)
