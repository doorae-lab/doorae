"""TheTable TUI — Textual 기반 회의 인터페이스"""

from __future__ import annotations

import colorsys
import random
import time
from typing import TYPE_CHECKING, Any, cast

from rich.markup import escape
from rich.spinner import Spinner
from rich.text import Text
from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.message import Message
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Collapsible, Footer, Header, Input, Markdown, Static, Tree
from textual.worker import WorkerCancelled
from thetable.config import Settings
from thetable.graph.constants import (
    PARTICIPANT_STATUS_EMOJI,
    PARTICIPANT_STATUS_TEXT,
    STATUS_EMOJI,
)
from thetable.interfaces.engine import MeetingEngine
from thetable.interfaces.time_utils import format_elapsed

if TYPE_CHECKING:
    from thetable.core.profile import AgentProfile
    from thetable.graph.input_provider import TuiInputProvider
    from textual.widgets._tree import TreeNode
    from textual.timer import Timer


def _is_delegated(tags: list[str]) -> bool:
    """delegated_by: 태그 여부 확인."""
    return any(tag.startswith("delegated_by:") for tag in tags)


def _random_speaker_color() -> str:
    """터미널 다크 배경에서 읽기 좋은 랜덤 hex 색상 생성."""
    h = random.random()
    s = random.uniform(0.6, 1.0)
    l = random.uniform(0.45, 0.65)
    r, g, b = colorsys.hls_to_rgb(h, l, s)
    return f"#{int(r * 255):02x}{int(g * 255):02x}{int(b * 255):02x}"


class SpinnerWidget(Widget):
    """rich.spinner 기반 애니메이션 위젯."""

    DEFAULT_CSS = """
    SpinnerWidget {
        height: 1;
        width: 1fr;
        padding: 0 1;
        color: $text-muted;
    }
    """

    def __init__(self, label: str, color: str | None = None) -> None:
        super().__init__()
        self._label = label
        self._spinner = Spinner("dots")
        self._color = color

    def render(self) -> Text:
        text = self._spinner.render(time.monotonic())
        if self._color:
            return Text.assemble(text, f" {self._label}", style=self._color)
        return Text.assemble(text, f" {self._label}")

    def on_mount(self) -> None:
        self._refresh_timer = self.set_interval(1 / 12, self.refresh)

    def on_unmount(self) -> None:
        if hasattr(self, "_refresh_timer"):
            self._refresh_timer.stop()


class SpeechBubble(Widget):
    """단일 발언 위젯 — 스트리밍 중 Static, 완료 후 Markdown."""

    DEFAULT_CSS = """
    SpeechBubble {
        width: 1fr;
        height: auto;
        margin-bottom: 1;
        border-left: wide transparent;
        padding: 1 0 0 1;
        background: $surface-lighten-1;
    }
    SpeechBubble.delegated {
        margin: 1 0 1 2;
        opacity: 0.8;
        border-left: block $secondary;
        background: $surface-lighten-2;
    }
    SpeechBubble Markdown {
        padding: 1 1;
        height: auto;
    }
    SpeechBubble .bubble-body {
        padding: 1 1;
        height: auto;
    }
    SpeechBubble .bubble-header {
        height: auto;
        width: 1fr;
    }
    SpeechBubble .bubble-header Static {
        width: auto;
    }
    SpeechBubble .bubble-header SpinnerWidget {
        width: auto;
    }
    SpeechBubble Collapsible {
        margin: 0 0 0 1;
        padding: 0;
        height: auto;
    }
    SpeechBubble .tool-indicator {
        color: $text-muted;
        padding: 0 1;
        height: auto;
    }
    """

    def __init__(self, speaker: str, color: str, is_delegated: bool = False) -> None:
        super().__init__(classes="delegated" if is_delegated else "")
        self._speaker = speaker
        self._color = color
        self._buffer = ""
        self.is_delegated = is_delegated
        self._body: Static | None = None
        self._tool_indicator: SpinnerWidget | None = None
        self._header_spinner: SpinnerWidget | None = None

    def on_mount(self) -> None:
        if not self.is_delegated:
            self.styles.border_left = ("wide", self._color)

    def compose(self) -> ComposeResult:
        with Horizontal(classes="bubble-header"):
            if self.is_delegated:
                yield Static(f"[dim] {self._speaker} (위임)[/dim]")
            else:
                yield Static(f"[bold {self._color}] {self._speaker}[/bold {self._color}]")
            self._header_spinner = SpinnerWidget("", self._color)
            yield self._header_spinner
        self._body = Static("", classes="bubble-body")
        yield self._body

    def append_token(self, token: str) -> None:
        self._buffer += token
        if self._body is not None:
            if self.is_delegated:
                self._body.update(f"[dim]{escape(self._buffer)}[/dim]")
            else:
                self._body.update(self._buffer)

    def show_tool_started(self, tool_name: str) -> None:
        """tool 호출 시작 — spinner 인디케이터 표시."""
        self._tool_indicator = SpinnerWidget(f"⚙ {tool_name}")
        self.mount(self._tool_indicator)

    def show_tool_ended(self) -> None:
        """tool 호출 완료 — spinner 제거."""
        if self._tool_indicator is not None:
            self._tool_indicator.remove()
            self._tool_indicator = None

    def finalize(self) -> None:
        """발언 완료 시 body를 Markdown으로 교체, spinner 정리."""
        if self._header_spinner is not None:
            self._header_spinner.remove()
            self._header_spinner = None
        if self._body is not None:
            self._body.remove()
            self._body = None
        if self._tool_indicator is not None:
            self._tool_indicator.remove()
            self._tool_indicator = None
        self.mount(Markdown(self._buffer))


class TokenStreamed(Message):
    def __init__(self, token: str, agent_name: str, is_delegated: bool = False) -> None:
        super().__init__()
        self.token = token
        self.agent_name = agent_name
        self.is_delegated = is_delegated


class SpeakerChanged(Message):
    def __init__(self, speaker: str, pending: list[str], is_delegated: bool = False) -> None:
        super().__init__()
        self.speaker = speaker
        self.pending = pending
        self.is_delegated = is_delegated


class AgendaUpdated(Message):
    def __init__(self, agendas: list[dict[str, object]], current_idx: int) -> None:
        super().__init__()
        self.agendas = agendas
        self.current_idx = current_idx


class HumanTurnStarted(Message):
    def __init__(self, username: str) -> None:
        super().__init__()
        self.username = username


class TurnCompleted(Message):
    def __init__(self, speaker: str, is_delegated: bool = False) -> None:
        super().__init__()
        self.speaker = speaker
        self.is_delegated = is_delegated


class ToolCallStarted(Message):
    def __init__(self, tool_name: str) -> None:
        super().__init__()
        self.tool_name = tool_name


class ToolCallEnded(Message):
    def __init__(self, tool_name: str) -> None:
        super().__init__()
        self.tool_name = tool_name


class ParticipantStatusChanged(Message):
    def __init__(self, participant_name: str, status: str) -> None:
        super().__init__()
        self.participant_name = participant_name
        self.status = status


class MeetingEnded(Message):
    def __init__(self, agendas: list[dict[str, object]], speaker_counts: dict[str, int]) -> None:
        super().__init__()
        self.agendas = agendas
        self.speaker_counts = speaker_counts


class StreamError(Message):
    def __init__(self, error: str) -> None:
        super().__init__()
        self.error = error


class TuiMeetingCallback:
    """MeetingEngine callback adapter that reuses existing Textual messages."""

    def __init__(self, app: "MeetingTuiApp") -> None:
        self._app = app

    async def on_raw_event(self, event: dict[str, object]) -> None:
        _ = event

    async def on_speaker_changed(self, speaker: str, is_delegated: bool) -> None:
        self._app.post_message(SpeakerChanged(speaker=speaker, pending=[], is_delegated=is_delegated))

    async def on_token(self, content: str, speaker: str, is_delegated: bool) -> None:
        self._app.post_message(
            TokenStreamed(token=content, agent_name=speaker, is_delegated=is_delegated)
        )

    async def on_turn_completed(self, speaker: str, is_delegated: bool) -> None:
        self._app.post_message(TurnCompleted(speaker=speaker, is_delegated=is_delegated))

    async def on_human_turn_started(self, username: str) -> None:
        self._app.post_message(HumanTurnStarted(username=username))

    async def on_agenda_updated(
        self,
        agendas: list[dict[str, object]],
        current_idx: int,
    ) -> None:
        self._app.post_message(AgendaUpdated(agendas=agendas, current_idx=current_idx))

    async def on_meeting_ended(
        self,
        agendas: list[dict[str, object]],
        speaker_counts: dict[str, int],
    ) -> None:
        self._app.post_message(MeetingEnded(agendas=agendas, speaker_counts=speaker_counts))

    async def on_pending_speakers_changed(self, pending_speakers: list[str]) -> None:
        _ = pending_speakers

    async def on_participant_status_changed(self, participant_name: str, status: str) -> None:
        self._app.post_message(ParticipantStatusChanged(participant_name, status))

    async def on_tool_call(self, name: str, status: str) -> None:
        if status == "started":
            self._app.post_message(ToolCallStarted(tool_name=name))
        elif status == "ended":
            self._app.post_message(ToolCallEnded(tool_name=name))


class AgendaPanel(Static):
    """안건 진행 상태 패널."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._timer_str: str = "00:00"
        self._meeting_start_time: float | None = None
        self._last_agendas: list[dict[str, object]] = []
        self._current_idx: int = 0

    def update_timer(self, timer_str: str) -> None:
        self._timer_str = timer_str
        self.update_agendas(self._last_agendas, self._current_idx)

    def update_meeting_start_time(self, meeting_start_time: float) -> None:
        self._meeting_start_time = meeting_start_time
        self.update_agendas(self._last_agendas, self._current_idx)

    def update_agendas(self, agendas: list[dict[str, object]], current_idx: int) -> None:
        self._last_agendas = agendas
        self._current_idx = current_idx

        lines = [f"[bold cyan]⏱ 총 경과: {self._timer_str}[/bold cyan]", "─" * 30]
        now = time.time()

        for i, agenda in enumerate(agendas):
            raw_status = agenda.get("status", "pending")
            status = raw_status if isinstance(raw_status, str) else "pending"
            emoji = STATUS_EMOJI.get(status, "❓")
            title = agenda.get("title", "")
            marker = " ◀" if i == current_idx else ""
            elapsed_str = ""

            if status == "in_progress":
                raw_start = agenda.get("start_time")
                agenda_start = (
                    float(raw_start)
                    if isinstance(raw_start, (int, float))
                    else self._meeting_start_time
                )
                if agenda_start is not None:
                    elapsed_seconds = max(0, int(now - agenda_start))
                    elapsed_str = f" [{format_elapsed(elapsed_seconds)}]"
            elif status == "completed":
                raw_start = agenda.get("start_time")
                raw_end = agenda.get("end_time")
                if isinstance(raw_start, (int, float)) and isinstance(raw_end, (int, float)):
                    elapsed_seconds = max(0, int(raw_end - raw_start))
                    elapsed_str = f" [{format_elapsed(elapsed_seconds)}]"

            lines.append(f"{emoji} {i + 1}. {title}{elapsed_str}{marker}")
            if agenda.get("decision"):
                lines.append(f"   └─ {agenda['decision']}")
        self.update("\n".join(lines))


class ParticipantPanel(Vertical):
    """참여자 계층 및 상태 패널."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._top_profiles: dict[str, AgentProfile] = {}
        self._flat_profiles: dict[str, AgentProfile] = {}
        self._statuses: dict[str, str] = {}
        self._participant_nodes: dict[str, TreeNode[Any]] = {}

    def compose(self) -> ComposeResult:
        yield Static("[bold]👥 참여자[/bold]")
        yield Tree("participants", id="participant-tree")

    def on_mount(self) -> None:
        tree = self.query_one("#participant-tree", Tree)
        tree.show_root = False

    def initialize(
        self,
        top_profiles: dict[str, AgentProfile],
        flat_profiles: dict[str, AgentProfile],
    ) -> None:
        self._top_profiles = top_profiles
        self._flat_profiles = flat_profiles
        self._statuses = {name: "idle" for name in flat_profiles}
        self._rebuild_tree()

    def update_status(self, participant_name: str, status: str) -> None:
        self._statuses[participant_name] = status
        node = self._participant_nodes.get(participant_name)
        profile = self._flat_profiles.get(participant_name)
        if node is not None:
            node.set_label(self._format_label(participant_name, profile))

    def _rebuild_tree(self) -> None:
        tree = self.query_one("#participant-tree", Tree)
        tree.root.remove_children()
        self._participant_nodes = {}
        for profile in self._top_profiles.values():
            self._add_profile_node(tree.root, profile, is_top_level=True)
        tree.root.expand()

    def _add_profile_node(
        self,
        parent_node: TreeNode[Any],
        profile: AgentProfile,
        is_top_level: bool,
    ) -> None:
        node = parent_node.add(
            self._format_label(profile.name, profile),
            expand=is_top_level,
        )
        if not is_top_level and profile.agents:
            node.collapse()
        self._participant_nodes[profile.name] = node
        for child in profile.agents or []:
            self._add_profile_node(node, child, is_top_level=False)

    def _format_label(self, name: str, profile: AgentProfile | None) -> str:
        status = self._statuses.get(name, "idle")
        status_emoji = PARTICIPANT_STATUS_EMOJI.get(status, "⚪")
        status_text = PARTICIPANT_STATUS_TEXT.get(status, status)
        role = profile.role if profile else "participant"
        return f"{status_emoji} {name} ({role}) [{status_text}]"


class MeetingTuiApp(App[None]):
    DEFAULT_CSS = """
    Screen {
        layout: vertical;
    }
    Horizontal {
        height: 1fr;
    }
    #right-sidebar {
        width: 55;
    }
    #agenda-panel {
        height: 1fr;
        padding: 1 2;
        border-top: solid $primary;
        border-bottom: solid $primary;
        border-left: solid $primary;
        border-right: solid $primary;
    }
    #participant-panel {
        height: auto;
        max-height: 40%;
        padding: 1 1;
        border-top: solid $primary;
        border-bottom: solid $primary;
        border-left: solid $primary;
        border-right: solid $primary;
    }
    #participant-tree {
        height: 1fr;
        margin-top: 1;
        padding: 1 2;
    }
    #main-panel {
        width: 1fr;
    }
    #conversation-scroll {
        height: 1fr;
        padding: 1 2;
    }
    #human-input-panel {
        height: auto;
        display: none;
        border-top: solid $accent;
        padding: 0 1;
        background: $surface;
    }
    #human-input-panel.visible {
        display: block;
    }
    #human-input-label {
        color: $accent;
        padding: 0 0 0 1;
    }
    #input-area {
        height: 3;
    }
    """

    TITLE = "TheTable"
    BINDINGS = [
        Binding("ctrl+c", "quit", "종료", show=False),
        Binding("ctrl+q", "quit", "종료"),
        Binding("question_mark", "help", "도움말"),
        Binding("pageup", "scroll_up", "Page Up", show=False),
        Binding("pagedown", "scroll_down", "Page Down", show=False),
        Binding("d", "toggle_delegated", "위임 표시"),
    ]

    current_speaker: reactive[str] = reactive("")
    current_agenda_idx: reactive[int] = reactive(0)
    meeting_status: reactive[str] = reactive("starting")
    input_enabled: reactive[bool] = reactive(False)
    show_delegated: reactive[bool] = reactive(True)

    def __init__(
        self,
        settings: Settings,
        profiles_path: str,
        initial_message: str,
        mcp_tools: dict[str, list[object]] | None = None,
    ) -> None:
        super().__init__()
        self._settings = settings
        self._profiles_path = profiles_path
        self._initial_message = initial_message
        self._mcp_tools = mcp_tools
        self._engine: MeetingEngine | None = None
        self._workflow: Any = None
        self._initial_state: dict[str, object] = {}
        self._graph_config: Any = {}
        self._human_names: list[str] = []
        self._last_agendas: list[dict[str, object]] = []
        self._last_speaker_counts: dict[str, int] = {}
        self._input_provider: TuiInputProvider | None = None
        self._current_bubble: SpeechBubble | None = None
        self._current_delegated_bubble: SpeechBubble | None = None
        self._current_delegated_speaker: str = ""
        self._current_human_speaker: str = ""
        self._speaker_colors: dict[str, str] = {}
        self._meeting_start_time: float = 0.0
        self._timer_interval: Timer | None = None
        self._participant_statuses: dict[str, str] = {}
        self._full_text: str = ""

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal():
            with Vertical(id="main-panel"):
                yield VerticalScroll(id="conversation-scroll")
            with Vertical(id="right-sidebar"):
                yield AgendaPanel(id="agenda-panel")
                yield ParticipantPanel(id="participant-panel")
        with Vertical(id="human-input-panel"):
            yield Static("의견을 입력하세요", id="human-input-label")
            yield Input(id="input-area", placeholder="의견을 입력하세요 (Enter로 전송, 빈 입력 시 스킵)")
        yield Footer()

    async def on_mount(self) -> None:
        from thetable.graph.input_provider import TuiInputProvider

        self._input_provider = TuiInputProvider()
        self._engine = MeetingEngine(
            initial_message=self._initial_message,
            settings=self._settings,
            profiles_path=self._profiles_path,
            mcp_tools=self._mcp_tools or {},
            input_provider=self._input_provider,
        )
        setup_state = self._engine.setup()
        self._workflow = setup_state.workflow
        self._initial_state = setup_state.initial_state
        self._graph_config = setup_state.graph_config
        self._human_names = [name.lower() for name in setup_state.human_names]

        participant_panel = self.query_one("#participant-panel", ParticipantPanel)
        participant_panel.initialize(setup_state.top_profiles, setup_state.all_profiles)
        self._participant_statuses = dict(self._engine.runtime_state.participant_statuses)
        self._initial_state["participant_statuses"] = dict(self._participant_statuses)

        raw_start_time = self._initial_state.get("start_time")
        if isinstance(raw_start_time, (int, float)):
            self._meeting_start_time = float(raw_start_time)
        else:
            self._meeting_start_time = time.time()
            self._initial_state["start_time"] = self._meeting_start_time
        initial_agendas = self._initial_state.get("agendas", [])
        if isinstance(initial_agendas, list):
            self._last_agendas = cast(list[dict[str, object]], initial_agendas)

        agenda_panel = self.query_one("#agenda-panel", AgendaPanel)
        agenda_panel.update_meeting_start_time(self._meeting_start_time)
        agenda_panel.update_agendas(self._last_agendas, 0)
        self._timer_interval = self.set_interval(1.0, self._tick_timer)

        self.run_meeting_worker()

    @work(exclusive=True)
    async def run_meeting_worker(self) -> None:
        try:
            if self._engine is None:
                return
            self.meeting_status = "running"
            await self._engine.run(TuiMeetingCallback(self))
        except WorkerCancelled:
            pass  # Ctrl+C/Q 종료 시 정상 취소 — 무시
        except Exception as e:
            self.post_message(StreamError(error=str(e)))

    def _get_speaker_color(self, speaker: str) -> str:
        if speaker not in self._speaker_colors:
            self._speaker_colors[speaker] = _random_speaker_color()
        return self._speaker_colors[speaker]

    def _mount_bubble(self, bubble: SpeechBubble) -> None:
        """bubble을 conversation-scroll에 마운트하고 끝으로 스크롤."""
        scroll = self.query_one("#conversation-scroll", VerticalScroll)
        if bubble.is_delegated and not self.show_delegated:
            bubble.display = False
        scroll.mount(bubble)
        if bubble.display:
            scroll.scroll_end(animate=False)

    def watch_current_speaker(self, speaker: str) -> None:
        self.sub_title = f"발언자: {speaker}" if speaker else ""

    def watch_current_agenda_idx(self, idx: int) -> None:
        agenda_panel = self.query_one("#agenda-panel", AgendaPanel)
        agenda_panel.update_agendas(self._last_agendas, idx)

    def watch_show_delegated(self, show: bool) -> None:
        for collapsible in self.query(Collapsible):
            if getattr(collapsible, "is_delegated", False):
                collapsible.display = show

    def _tick_timer(self) -> None:
        if self.meeting_status == "ended":
            return
        elapsed_seconds = max(0, int(time.time() - self._meeting_start_time))
        timer_str = format_elapsed(elapsed_seconds)
        agenda_panel = self.query_one("#agenda-panel", AgendaPanel)
        agenda_panel.update_timer(timer_str)

    def watch_input_enabled(self, enabled: bool) -> None:
        panel = self.query_one("#human-input-panel", Vertical)
        input_area = self.query_one("#input-area", Input)
        if enabled:
            panel.add_class("visible")
            input_area.focus()
        else:
            panel.remove_class("visible")

    def watch_meeting_status(self, status: str) -> None:
        if status == "ended":
            self._render_summary()

    def on_token_streamed(self, event: TokenStreamed) -> None:
        if event.is_delegated:
            if self._current_delegated_bubble:
                self._current_delegated_bubble.append_token(event.token)
        else:
            if self._current_bubble:
                self._current_bubble.append_token(event.token)
        scroll = self.query_one("#conversation-scroll", VerticalScroll)
        scroll.scroll_end(animate=False)

    def on_speaker_changed(self, event: SpeakerChanged) -> None:
        if event.is_delegated:
            self._current_delegated_speaker = event.speaker
            self.post_message(ParticipantStatusChanged(event.speaker, "speaking"))
            bubble = SpeechBubble(
                speaker=event.speaker,
                color=self._get_speaker_color(event.speaker),
                is_delegated=True,
            )
            self._current_delegated_bubble = bubble
            if self._current_bubble:
                collapsible = Collapsible(
                    bubble,
                    title=f"{event.speaker} (위임)",
                    collapsed=False,
                )
                if not self.show_delegated:
                    collapsible.display = False
                collapsible.is_delegated = True  # type: ignore[attr-defined]
                self._current_bubble.mount(collapsible)
                scroll = self.query_one("#conversation-scroll", VerticalScroll)
                scroll.scroll_end(animate=False)
            else:
                self._mount_bubble(bubble)
            return

        self._current_delegated_bubble = None
        self._current_delegated_speaker = ""
        self._current_human_speaker = ""
        prev_speaker = self.current_speaker
        self.current_speaker = event.speaker
        self.input_enabled = False
        if prev_speaker and prev_speaker != event.speaker:
            self.post_message(ParticipantStatusChanged(prev_speaker, "idle"))
        self.post_message(ParticipantStatusChanged(event.speaker, "speaking"))
        bubble = SpeechBubble(
            speaker=event.speaker,
            color=self._get_speaker_color(event.speaker),
            is_delegated=False,
        )
        self._current_bubble = bubble
        self._mount_bubble(bubble)

    def on_agenda_updated(self, event: AgendaUpdated) -> None:
        self._last_agendas = event.agendas
        agenda_panel = self.query_one("#agenda-panel", AgendaPanel)
        agenda_panel.update_meeting_start_time(self._meeting_start_time)
        self.current_agenda_idx = event.current_idx

    def on_human_turn_started(self, event: HumanTurnStarted) -> None:
        label = self.query_one("#human-input-label", Static)
        agenda_title = self._get_current_agenda_title()
        self._current_human_speaker = event.username
        label.update(escape(f"[{event.username}의 차례] {agenda_title}"))
        self.post_message(ParticipantStatusChanged(event.username, "waiting_input"))
        self.input_enabled = True
        scroll = self.query_one("#conversation-scroll", VerticalScroll)
        scroll.mount(
            Static(f"[bold yellow]── {event.username}님 차례입니다 ──[/bold yellow]")
        )
        scroll.scroll_end(animate=False)

    def on_turn_completed(self, event: TurnCompleted) -> None:
        if event.is_delegated:
            self._current_delegated_speaker = ""
            if self._current_delegated_bubble:
                self._current_delegated_bubble.finalize()
                self._current_delegated_bubble = None
            self.post_message(ParticipantStatusChanged(event.speaker, "idle"))
            return
        if self._current_bubble:
            self._current_bubble.finalize()
            # bubble 참조 유지 — tool 호출이 뒤따를 수 있으므로
            # 다음 speaker 변경 시 None으로 초기화됨
        if event.speaker:
            self.post_message(ParticipantStatusChanged(event.speaker, "idle"))

    def on_tool_call_started(self, event: ToolCallStarted) -> None:
        if self.current_speaker:
            self.post_message(ParticipantStatusChanged(self.current_speaker, "tool_calling"))
        active_bubble = self._current_delegated_bubble or self._current_bubble
        if active_bubble:
            active_bubble.show_tool_started(event.tool_name)

    def on_tool_call_ended(self, event: ToolCallEnded) -> None:
        if self.current_speaker:
            self.post_message(ParticipantStatusChanged(self.current_speaker, "speaking"))
        active_bubble = self._current_delegated_bubble or self._current_bubble
        if active_bubble:
            active_bubble.show_tool_ended()

    def on_participant_status_changed(self, event: ParticipantStatusChanged) -> None:
        self._participant_statuses[event.participant_name] = event.status
        participant_panel = self.query_one("#participant-panel", ParticipantPanel)
        participant_panel.update_status(event.participant_name, event.status)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        submitted_value = event.value
        if self._input_provider is not None:
            self._input_provider.submit_input(submitted_value)
        if submitted_value.strip() and self._current_human_speaker:
            bubble = SpeechBubble(
                speaker=self._current_human_speaker,
                color=self._get_speaker_color(self._current_human_speaker),
            )
            bubble.append_token(submitted_value)
            self._mount_bubble(bubble)
            self.call_after_refresh(bubble.finalize)
        event.input.clear()
        self.input_enabled = False
        self._current_human_speaker = ""

    def on_meeting_ended(self, event: MeetingEnded) -> None:
        self._last_agendas = event.agendas
        self._last_speaker_counts = event.speaker_counts
        if self._timer_interval is not None:
            self._timer_interval.stop()
            self._timer_interval = None
        self._tick_timer()
        self.meeting_status = "ended"

    def on_stream_error(self, event: StreamError) -> None:
        if self._timer_interval is not None:
            self._timer_interval.stop()
            self._timer_interval = None
        self.meeting_status = "ended"
        self._full_text = f"⚠ 오류: {event.error}"
        scroll = self._get_conversation_scroll()
        if scroll is None:
            return
        scroll.mount(Static(f"[bold yellow]⚠ 오류: {event.error}[/bold yellow]"))
        scroll.scroll_end(animate=False)

    def on_resize(self) -> None:
        sidebar = self.query_one("#right-sidebar", Vertical)
        sidebar.display = self.size.width >= 100

    async def action_quit(self) -> None:
        self.workers.cancel_all()
        self.exit()

    def action_help(self) -> None:
        self.notify(
            "Ctrl+C/Ctrl+Q: 종료\n?: 도움말\nPageUp/Down: 스크롤\nd: 위임 발언 표시/숨김",
            title="단축키",
            timeout=5,
        )

    def action_toggle_delegated(self) -> None:
        self.show_delegated = not self.show_delegated
        status = "표시" if self.show_delegated else "숨김"
        self.notify(f"위임 발언 {status}", timeout=2)

    def action_scroll_up(self) -> None:
        self.query_one("#conversation-scroll", VerticalScroll).scroll_page_up()

    def action_scroll_down(self) -> None:
        self.query_one("#conversation-scroll", VerticalScroll).scroll_page_down()

    def _render_summary(self) -> None:
        total_elapsed_seconds = max(0, int(time.time() - self._meeting_start_time))
        lines = [
            "## 📋 회의 요약",
            "",
            f"**⏱ 총 경과: {format_elapsed(total_elapsed_seconds)}**",
            "",
        ]
        for agenda in self._last_agendas:
            raw_status = agenda.get("status", "pending")
            status = raw_status if isinstance(raw_status, str) else "pending"
            emoji = STATUS_EMOJI.get(status, "❓")
            title = agenda.get("title", "")
            decision = agenda.get("decision", "-")
            lines.append(f"- {emoji} **{title}**")
            lines.append(f"  - 결정: {decision}")
            duration = ""
            if status == "in_progress":
                raw_start = agenda.get("start_time")
                agenda_start = (
                    float(raw_start)
                    if isinstance(raw_start, (int, float))
                    else self._meeting_start_time
                )
                duration = format_elapsed(max(0, int(time.time() - agenda_start)))
            elif status == "completed":
                raw_start = agenda.get("start_time")
                raw_end = agenda.get("end_time")
                if isinstance(raw_start, (int, float)) and isinstance(raw_end, (int, float)):
                    duration = format_elapsed(max(0, int(raw_end - raw_start)))
            if duration:
                lines.append(f"  - 소요: {duration}")
        lines.extend(["", "*Ctrl+C로 종료*"])
        self._full_text = "\n".join(lines)
        scroll = self._get_conversation_scroll()
        if scroll is None:
            return
        scroll.mount(Markdown(self._full_text))
        scroll.scroll_end(animate=False)

    def _get_current_agenda_title(self) -> str:
        if not self._last_agendas:
            return "안건 미지정"
        if self.current_agenda_idx < 0 or self.current_agenda_idx >= len(self._last_agendas):
            return "안건 미지정"
        title = self._last_agendas[self.current_agenda_idx].get("title")
        return str(title) if title else "안건 미지정"

    def _get_conversation_scroll(self) -> VerticalScroll | None:
        try:
            return self.query_one("#conversation-scroll", VerticalScroll)
        except Exception:
            return None
