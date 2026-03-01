"""TheTable TUI — Textual 기반 회의 인터페이스"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import Footer, Header, Input, RichLog, Static
from textual.worker import WorkerCancelled
from thetable.config import Settings
from thetable.graph.constants import AGENT_COLORS, STATUS_EMOJI
if TYPE_CHECKING:
    from thetable.graph.input_provider import TuiInputProvider


class TokenStreamed(Message):
    def __init__(self, token: str, agent_name: str) -> None:
        super().__init__()
        self.token = token
        self.agent_name = agent_name


class SpeakerChanged(Message):
    def __init__(self, speaker: str, pending: list[str]) -> None:
        super().__init__()
        self.speaker = speaker
        self.pending = pending


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
    def __init__(self, speaker: str) -> None:
        super().__init__()
        self.speaker = speaker


class MeetingEnded(Message):
    def __init__(self, agendas: list[dict[str, object]], speaker_counts: dict[str, int]) -> None:
        super().__init__()
        self.agendas = agendas
        self.speaker_counts = speaker_counts


class StreamError(Message):
    def __init__(self, error: str) -> None:
        super().__init__()
        self.error = error


class AgendaPanel(Static):
    """안건 진행 상태 패널."""

    def update_agendas(self, agendas: list[dict[str, object]], current_idx: int) -> None:
        lines = []
        for i, agenda in enumerate(agendas):
            raw_status = agenda.get("status", "pending")
            status = raw_status if isinstance(raw_status, str) else "pending"
            emoji = STATUS_EMOJI.get(status, "❓")
            title = agenda.get("title", "")
            marker = " ◀" if i == current_idx else ""
            lines.append(f"{emoji} {i + 1}. {title}{marker}")
            if agenda.get("decision"):
                lines.append(f"   └─ {agenda['decision']}")
        self.update("\n".join(lines))


class MeetingTuiApp(App[None]):
    DEFAULT_CSS = """
    Screen {
        layout: vertical;
    }
    Horizontal {
        height: 1fr;
    }
    #agenda-panel {
        width: 25;
        border-right: solid $primary;
        padding: 1;
    }
    #main-panel {
        width: 1fr;
    }
    #conversation {
        height: 1fr;
    }
    #input-area {
        height: 3;
        display: none;
    }
    #input-area.visible {
        display: block;
    }
    #current-stream {
        height: auto;
        padding: 0 1;
        color: $text-muted;
    }
    """

    TITLE = "TheTable"
    BINDINGS = [
        Binding("ctrl+c", "quit", "종료", show=False),
        Binding("ctrl+q", "quit", "종료"),
        Binding("question_mark", "help", "도움말"),
    ]

    current_speaker: reactive[str] = reactive("")
    current_agenda_idx: reactive[int] = reactive(0)
    meeting_status: reactive[str] = reactive("starting")
    input_enabled: reactive[bool] = reactive(False)

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
        self._workflow: Any = None
        self._initial_state: dict[str, object] = {}
        self._graph_config: Any = {}
        self._human_names: list[str] = []
        self._last_agendas: list[dict[str, object]] = []
        self._last_speaker_counts: dict[str, int] = {}
        self._input_provider: TuiInputProvider | None = None
        self._token_buffer: str = ""

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal():
            yield AgendaPanel(id="agenda-panel")
            with Vertical(id="main-panel"):
                yield RichLog(id="conversation", auto_scroll=True, wrap=True, max_lines=2000)
                yield Static(id="current-stream")
        yield Input(id="input-area", placeholder="의견을 입력하세요 (Enter로 전송, 빈 입력 시 스킵)")
        yield Footer()


    async def on_mount(self) -> None:
        from thetable.core.agenda import load_agendas
        from thetable.core.profile import load_agent_profiles
        from thetable.graph.input_provider import TuiInputProvider
        from thetable.graph.workflow import build_initial_state, create_meeting_workflow

        self._input_provider = TuiInputProvider()
        self._workflow = create_meeting_workflow(
            profiles_path=self._profiles_path,
            mcp_tools=self._mcp_tools or {},
            input_provider=self._input_provider,
        )

        profiles = load_agent_profiles(self._profiles_path)
        self._human_names = [name.lower() for name, p in profiles.items() if p.is_human]

        agendas = load_agendas(str(self._settings.agendas_path))
        self._initial_state = build_initial_state(
            self._settings, self._initial_message, self._human_names, agendas
        )
        self._graph_config = {"recursion_limit": self._settings.recursion_limit}
        initial_agendas = self._initial_state.get("agendas", [])
        if isinstance(initial_agendas, list):
            self._last_agendas = cast(list[dict[str, object]], initial_agendas)

        agenda_panel = self.query_one("#agenda-panel", AgendaPanel)
        agenda_panel.update_agendas(self._last_agendas, 0)

        self.run_meeting_worker()

    @work(exclusive=True)
    async def run_meeting_worker(self) -> None:
        """LangGraph 워크플로우 이벤트를 소비하고 Textual 메시지로 변환한다."""
        try:
            if self._workflow is None:
                return
            self.meeting_status = "running"
            async for event in self._workflow.astream_events(
                self._initial_state,
                config=cast(Any, self._graph_config),
                version="v2",
            ):
                kind = event["event"]
                if kind == "on_chain_start":
                    self._handle_worker_chain_start(event)
                elif kind == "on_chat_model_start":
                    self._handle_worker_chat_model_start(event)
                elif kind == "on_chat_model_stream":
                    self._handle_worker_chat_model_stream(event)
                elif kind == "on_chat_model_end":
                    self._handle_worker_chat_model_end(event)
                elif kind == "on_chain_end":
                    self._handle_worker_chain_end(event)
            self.post_message(
                MeetingEnded(
                    agendas=self._last_agendas,
                    speaker_counts=self._last_speaker_counts,
                )
            )
        except WorkerCancelled:
            pass
        except Exception as e:
            self.post_message(StreamError(error=str(e)))

    def _handle_worker_chain_start(self, event: Any) -> None:
        if event.get("name") == "process_response":
            input_data = event.get("data", {}).get("input", {})
            agendas = input_data.get("agendas", [])
            current_idx = input_data.get("current_agenda_idx", 0)
            self.post_message(AgendaUpdated(agendas=agendas, current_idx=current_idx))

        event_name = str(event.get("name", ""))
        if event_name.lower() in self._human_names:
            self.post_message(HumanTurnStarted(username=event_name))

    def _handle_worker_chat_model_start(self, event: Any) -> None:
        speaker = event.get("name")
        if not speaker or speaker == "ChatOpenAI":
            tags = event.get("tags", [])
            for tag in tags:
                if tag.startswith("speaker:"):
                    speaker = tag.replace("speaker:", "")
                    break

        if speaker and speaker not in ("ChatOpenAI", "RunnableSequence"):
            self.post_message(SpeakerChanged(speaker=speaker, pending=[]))

    def _handle_worker_chat_model_stream(self, event: Any) -> None:
        tags = event.get("tags", [])
        if "participant" not in tags:
            return

        chunk = event.get("data", {}).get("chunk")
        content = getattr(chunk, "content", "")
        if content:
            self.post_message(TokenStreamed(token=content, agent_name=self.current_speaker))

    def _handle_worker_chat_model_end(self, event: Any) -> None:
        tags = event.get("tags", [])
        if "participant" in tags:
            self.post_message(TurnCompleted(speaker=self.current_speaker))

    def _handle_worker_chain_end(self, event: Any) -> None:
        tags = event.get("tags", [])
        if "langgraph_node" not in tags:
            return

        try:
            idx = tags.index("langgraph_node")
            node_name = tags[idx + 1] if idx + 1 < len(tags) else None
        except (ValueError, IndexError):
            return

        if node_name != "process_response":
            return

        output_data = event.get("data", {}).get("output", {})
        pending = output_data.get("pending_speakers", [])
        self._last_agendas = output_data.get("agendas", self._last_agendas)
        self._last_speaker_counts = output_data.get("speaker_counts", self._last_speaker_counts)
        _ = pending

    def watch_current_speaker(self, speaker: str) -> None:
        self.sub_title = f"발언자: {speaker}" if speaker else ""

    def watch_current_agenda_idx(self, idx: int) -> None:
        agenda_panel = self.query_one("#agenda-panel", AgendaPanel)
        agenda_panel.update_agendas(self._last_agendas, idx)

    def watch_input_enabled(self, enabled: bool) -> None:
        input_area = self.query_one("#input-area", Input)
        if enabled:
            input_area.add_class("visible")
            input_area.focus()
        else:
            input_area.remove_class("visible")

    def watch_meeting_status(self, status: str) -> None:
        if status == "ended":
            log = self.query_one("#conversation", RichLog)
            self._render_summary(log)

    def _flush_token_buffer(self) -> None:
        if not self._token_buffer:
            return
        log = self.query_one("#conversation", RichLog)
        color_idx = hash(self.current_speaker) % len(AGENT_COLORS)
        color = AGENT_COLORS[color_idx]
        log.write(f"[{color}]{self._token_buffer}[/{color}]")
        self._token_buffer = ""
        self.query_one("#current-stream", Static).update("")

    def on_token_streamed(self, event: TokenStreamed) -> None:
        self._token_buffer += event.token
        stream = self.query_one("#current-stream", Static)
        color_idx = hash(event.agent_name) % len(AGENT_COLORS)
        color = AGENT_COLORS[color_idx]
        stream.update(f"[{color}]{self._token_buffer}[/{color}]")

    def on_speaker_changed(self, event: SpeakerChanged) -> None:
        self._flush_token_buffer()
        self.current_speaker = event.speaker
        log = self.query_one("#conversation", RichLog)
        log.write("")
        log.write(f"[bold cyan]── {event.speaker} ──[/bold cyan]")

    def on_agenda_updated(self, event: AgendaUpdated) -> None:
        self._last_agendas = event.agendas
        self.current_agenda_idx = event.current_idx

    def on_human_turn_started(self, event: HumanTurnStarted) -> None:
        self.input_enabled = True
        log = self.query_one("#conversation", RichLog)
        log.write(f"[bold yellow]── {event.username}님 차례입니다 ──[/bold yellow]")

    def on_turn_completed(self, event: TurnCompleted) -> None:
        self._flush_token_buffer()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if self._input_provider is not None:
            self._input_provider.submit_input(event.value)
        event.input.clear()
        self.input_enabled = False

    def on_meeting_ended(self, event: MeetingEnded) -> None:
        self._last_agendas = event.agendas
        self._last_speaker_counts = event.speaker_counts
        self.meeting_status = "ended"

    def on_stream_error(self, event: StreamError) -> None:
        log = self.query_one("#conversation", RichLog)
        log.write(f"[bold red]⚠ 오류: {event.error}[/bold red]")

    def on_resize(self) -> None:
        agenda_panel = self.query_one("#agenda-panel", AgendaPanel)
        agenda_panel.display = self.size.width >= 100

    async def action_quit(self) -> None:
        self.workers.cancel_all()
        self.exit()

    def action_help(self) -> None:
        self.notify(
            "Ctrl+C/Ctrl+Q: 종료\n?: 도움말",
            title="단축키",
            timeout=5,
        )

    def _render_summary(self, log: RichLog) -> None:
        log.write("")
        log.write("[bold]📋 회의 요약[/bold]")
        for agenda in self._last_agendas:
            raw_status = agenda.get("status", "pending")
            status = raw_status if isinstance(raw_status, str) else "pending"
            emoji = STATUS_EMOJI.get(status, "❓")
            title = agenda.get("title", "")
            decision = agenda.get("decision", "-")
            log.write(f"  {emoji} {title}")
            log.write(f"     결정: {decision}")
        if self._last_speaker_counts:
            log.write("")
            log.write("[bold]📊 발언 통계[/bold]")
            for speaker, count in self._last_speaker_counts.items():
                log.write(f"  {speaker}: {count}회")
        log.write("")
        log.write("[dim]Ctrl+C로 종료[/dim]")
