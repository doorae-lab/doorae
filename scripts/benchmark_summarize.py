#!/usr/bin/env python3
"""Summarize 최적화 벤치마크 스크립트.

서버 모드로 회의를 실행하고, 2개 WebSocket 클라이언트로 모니터링하며,
노드별 실행 시간을 측정한다.

Usage:
    uv run python3 scripts/benchmark_summarize.py [--runs 3] [--max-turns 20] [--port 9999]
"""

import argparse
import asyncio
import json
import os
import signal
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

import httpx
import websockets


# ============================================================================
# Configuration
# ============================================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PORT = 9999
DEFAULT_RUNS = 3
DEFAULT_MAX_TURNS = 20


def get_server_url(port: int) -> str:
    return f"http://localhost:{port}"


def get_ws_url(port: int, room_id: str, username: str) -> str:
    return f"ws://localhost:{port}/ws/{room_id}?username={username}&raw_events=true"


# ============================================================================
# Metric Collector (WebSocket client)
# ============================================================================

class MetricCollector:
    """WebSocket 클라이언트로 이벤트를 수집하고 타이밍을 측정한다."""

    def __init__(self, name: str):
        self.name = name
        self.events: list[dict] = []
        self.node_timings: dict[str, list[float]] = {}
        self.turn_timings: list[float] = []
        self.summarize_timings: list[float] = []
        self.llm_call_count = 0
        self._node_starts: dict[str, float] = {}
        self._turn_start: float | None = None
        self._meeting_ended = asyncio.Event()
        self._start_time: float = 0
        self._end_time: float = 0

    async def connect_and_collect(self, ws_url: str) -> None:
        """WebSocket에 연결하여 이벤트를 수집한다."""
        self._start_time = time.time()
        try:
            async with websockets.connect(ws_url) as ws:
                while not self._meeting_ended.is_set():
                    try:
                        raw = await asyncio.wait_for(ws.recv(), timeout=300)
                        event = json.loads(raw)
                        self._process_event(event)
                    except asyncio.TimeoutError:
                        print(f"  [{self.name}] Timeout waiting for events")
                        break
                    except websockets.exceptions.ConnectionClosed:
                        break
        except Exception as e:
            print(f"  [{self.name}] Connection error: {e}")
        finally:
            self._end_time = time.time()

    def _process_event(self, event: dict) -> None:
        """이벤트를 처리하고 타이밍을 기록한다."""
        self.events.append(event)
        event_type = event.get("type", "")
        now = time.time()

        # Raw LangGraph events
        if event_type == "on_chain_start":
            node_name = self._extract_node_name(event)
            if node_name:
                self._node_starts[node_name] = now
                if node_name == "participant":
                    self._turn_start = now

        elif event_type == "on_chain_end":
            node_name = self._extract_node_name(event)
            if node_name and node_name in self._node_starts:
                elapsed = now - self._node_starts.pop(node_name)
                self.node_timings.setdefault(node_name, []).append(elapsed)
                if node_name == "summarize":
                    self.summarize_timings.append(elapsed)

        elif event_type == "on_chat_model_start":
            self.llm_call_count += 1

        elif event_type == "on_chat_model_end":
            if self._turn_start is not None:
                pass  # turn timing handled by chain_end

        # Semantic events
        elif event_type == "semantic:turn_completed":
            if self._turn_start is not None:
                self.turn_timings.append(now - self._turn_start)
                self._turn_start = None

        elif event_type == "semantic:meeting_ended":
            self._meeting_ended.set()

    def _extract_node_name(self, event: dict) -> str | None:
        """이벤트에서 노드 이름을 추출한다."""
        # Raw event format
        name = event.get("name")
        if name in ("summarize", "process_response", "participant",
                     "refill_speakers", "route_next"):
            return name

        # Try metadata tags
        metadata = event.get("metadata", {})
        if isinstance(metadata, dict):
            tags = metadata.get("tags", [])
            if isinstance(tags, list):
                for tag in tags:
                    if isinstance(tag, str) and tag.startswith("graph:step:"):
                        return tag.split(":")[-1]
        return None

    def get_results(self) -> dict:
        """수집된 메트릭을 반환한다."""
        total_time = self._end_time - self._start_time if self._end_time else 0

        def stats(values: list[float]) -> dict:
            if not values:
                return {"count": 0, "avg": 0, "min": 0, "max": 0, "total": 0}
            return {
                "count": len(values),
                "avg": round(sum(values) / len(values), 3),
                "min": round(min(values), 3),
                "max": round(max(values), 3),
                "total": round(sum(values), 3),
            }

        return {
            "total_time_s": round(total_time, 2),
            "total_events": len(self.events),
            "llm_call_count": self.llm_call_count,
            "summarize": stats(self.summarize_timings),
            "turn": stats(self.turn_timings),
            "node_timings": {
                name: stats(times)
                for name, times in sorted(self.node_timings.items())
            },
        }


# ============================================================================
# Server Management
# ============================================================================

def start_server(port: int, max_turns: int) -> subprocess.Popen:
    """서버를 백그라운드에서 시작한다."""
    env = os.environ.copy()
    env["AGENT_PROFILES_PATH"] = "config/benchmark_profiles.yaml"
    env["AGENDAS_PATH"] = "config/benchmark_agendas.yaml"
    env["MAX_TURNS"] = str(max_turns)
    env["TUI_ENABLED"] = "false"
    env["LANGCHAIN_TRACING_V2"] = "true"
    env["LANGCHAIN_API_KEY"] = os.environ.get("LANGCHAIN_API_KEY", "")
    env["LANGCHAIN_PROJECT"] = os.environ.get("LANGCHAIN_PROJECT", "doorae-benchmark")

    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn",
         "doorae.server.app:create_app",
         "--host", "0.0.0.0",
         "--port", str(port),
         "--factory",
         "--log-level", "warning"],
        cwd=str(PROJECT_ROOT),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return proc


async def wait_for_server(port: int, timeout: float = 30) -> bool:
    """서버가 준비될 때까지 대기한다."""
    url = f"http://localhost:{port}/api/rooms"
    deadline = time.time() + timeout
    async with httpx.AsyncClient() as client:
        while time.time() < deadline:
            try:
                resp = await client.get(url)
                if resp.status_code == 200:
                    return True
            except httpx.ConnectError:
                pass
            await asyncio.sleep(0.5)
    return False


def stop_server(proc: subprocess.Popen) -> None:
    """서버를 종료한다."""
    proc.send_signal(signal.SIGTERM)
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()


# ============================================================================
# Single Benchmark Run
# ============================================================================

async def run_single_benchmark(port: int, run_id: int) -> dict:
    """단일 벤치마크 실행. 서버 + 2 클라이언트."""
    base_url = get_server_url(port)

    async with httpx.AsyncClient(base_url=base_url) as client:
        # 1. Room 생성
        resp = await client.post("/api/rooms", json={"name": f"bench-run-{run_id}"})
        resp.raise_for_status()
        room_id = resp.json()["id"]
        print(f"  [Run {run_id}] Room created: {room_id}")

        # 2. 두 개의 모니터링 클라이언트 준비
        collector1 = MetricCollector(f"monitor-1-run{run_id}")
        collector2 = MetricCollector(f"monitor-2-run{run_id}")

        ws_url1 = get_ws_url(port, room_id, f"monitor1_{run_id}")
        ws_url2 = get_ws_url(port, room_id, f"monitor2_{run_id}")

        # 3. WebSocket 클라이언트 연결 (백그라운드)
        ws_task1 = asyncio.create_task(collector1.connect_and_collect(ws_url1))
        ws_task2 = asyncio.create_task(collector2.connect_and_collect(ws_url2))

        # 잠시 대기하여 WS 연결 완료
        await asyncio.sleep(1.0)

        # 4. 워크플로우 시작
        print(f"  [Run {run_id}] Starting workflow...")
        try:
            resp = await client.post(f"/api/rooms/{room_id}/start", timeout=10.0)
            resp.raise_for_status()
            print(f"  [Run {run_id}] Workflow started")
        except httpx.HTTPStatusError as e:
            # 참가자가 없으면 human 없이 직접 시작 시도
            print(f"  [Run {run_id}] Start failed ({e.response.status_code}), "
                  f"retrying without participants check...")
            # Fallback: 직접 engine 실행은 서버 모드에서 불가, 에러 보고
            raise

        # 5. 회의 완료 대기
        print(f"  [Run {run_id}] Waiting for meeting to end...")
        try:
            await asyncio.wait_for(
                asyncio.gather(
                    collector1._meeting_ended.wait(),
                    collector2._meeting_ended.wait(),
                ),
                timeout=600,  # 10분 타임아웃
            )
        except asyncio.TimeoutError:
            print(f"  [Run {run_id}] Meeting timed out after 600s")

        # 6. WebSocket 종료
        collector1._meeting_ended.set()
        collector2._meeting_ended.set()
        await asyncio.gather(ws_task1, ws_task2, return_exceptions=True)

        # 7. Room 삭제
        await client.delete(f"/api/rooms/{room_id}")

    # 8. 결과 수집 (두 collector 중 이벤트 많은 쪽 사용)
    r1 = collector1.get_results()
    r2 = collector2.get_results()
    primary = r1 if r1["total_events"] >= r2["total_events"] else r2

    primary["run_id"] = run_id
    primary["collector_1_events"] = r1["total_events"]
    primary["collector_2_events"] = r2["total_events"]

    return primary


# ============================================================================
# Main
# ============================================================================

async def run_benchmark(runs: int, max_turns: int, port: int) -> None:
    """벤치마크를 N회 실행하고 결과를 비교한다."""
    print(f"=== Summarize Benchmark ===")
    print(f"  Runs: {runs}, Max turns: {max_turns}, Port: {port}")
    print(f"  Profiles: config/benchmark_profiles.yaml")
    print(f"  Agendas:  config/benchmark_agendas.yaml")
    print()

    # 서버 시작
    print("Starting server...")
    server_proc = start_server(port, max_turns)
    try:
        if not await wait_for_server(port):
            print("ERROR: Server failed to start")
            stderr = server_proc.stderr.read().decode() if server_proc.stderr else ""
            print(f"Server stderr: {stderr}")
            return

        print(f"Server ready on port {port}")
        print()

        # N회 실행
        results = []
        for i in range(1, runs + 1):
            print(f"--- Run {i}/{runs} ---")
            try:
                result = await run_single_benchmark(port, i)
                results.append(result)
                print(f"  Total: {result['total_time_s']}s, "
                      f"LLM calls: {result['llm_call_count']}, "
                      f"Summarize: {result['summarize']}")
            except Exception as e:
                print(f"  Run {i} FAILED: {e}")
                results.append({"run_id": i, "error": str(e)})
            print()

    finally:
        print("Stopping server...")
        stop_server(server_proc)

    # 결과 출력
    print("=== Results ===")
    output = {
        "timestamp": datetime.now().isoformat(),
        "config": {
            "runs": runs,
            "max_turns": max_turns,
            "profiles": "config/benchmark_profiles.yaml",
            "agendas": "config/benchmark_agendas.yaml",
        },
        "runs": results,
    }

    # 집계
    valid = [r for r in results if "error" not in r]
    if valid:
        avg_total = sum(r["total_time_s"] for r in valid) / len(valid)
        avg_llm = sum(r["llm_call_count"] for r in valid) / len(valid)
        avg_summarize_total = sum(r["summarize"]["total"] for r in valid) / len(valid)
        avg_turn = sum(r["turn"]["avg"] for r in valid) / len(valid) if valid[0]["turn"]["count"] else 0

        output["summary"] = {
            "avg_total_time_s": round(avg_total, 2),
            "avg_llm_calls": round(avg_llm, 1),
            "avg_summarize_total_s": round(avg_summarize_total, 3),
            "avg_turn_time_s": round(avg_turn, 3),
            "successful_runs": len(valid),
            "failed_runs": len(results) - len(valid),
        }
        print(json.dumps(output["summary"], indent=2))

    # JSON 파일 저장
    output_path = PROJECT_ROOT / "benchmark_results.json"
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print(f"\nResults saved to: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Summarize optimization benchmark")
    parser.add_argument("--runs", type=int, default=DEFAULT_RUNS, help="Number of runs")
    parser.add_argument("--max-turns", type=int, default=DEFAULT_MAX_TURNS, help="Max turns per meeting")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="Server port")
    args = parser.parse_args()

    asyncio.run(run_benchmark(args.runs, args.max_turns, args.port))


if __name__ == "__main__":
    main()
