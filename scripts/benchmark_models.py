
import asyncio
import argparse
import sys
import time
from typing import List, Dict

from langchain_core.messages import HumanMessage, AIMessage
from langchain_openai import ChatOpenAI
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

# Add project root to path
import os
sys.path.append(os.getcwd())

from thetable.config import get_settings

console = Console()

async def benchmark_model(model_name: str, base_url: str = None, api_key: str = None):
    console.print(f"[bold blue]Starting benchmark for {model_name}[/bold blue]")

    settings = get_settings()

    # Init Model
    try:
        kwargs = {
            "model": model_name,
            "temperature": 0.0,
            "max_tokens": 1024,
        }
        if base_url:
            kwargs["base_url"] = base_url
        if api_key:
            kwargs["api_key"] = api_key
        else:
            kwargs["api_key"] = settings.openai_api_key

        model = ChatOpenAI(**kwargs)
        console.print(f"✅ Model initialized: {model.__class__.__name__}")
    except Exception as e:
        console.print(f"[bold red]❌ Model initialization failed: {e}[/bold red]")
        return

    results = []

    # NOTE: Agenda Extraction benchmark removed (agenda_manager 모듈 삭제됨)
    # 안건 관리는 이제 에이전트 Tool(propose/approve/reject)로 처리됩니다.

    # Test: Mention Extraction (LLM 기반)
    console.print("\n[bold]Test: Mention Extraction[/bold]")
    content = "PM님, 그리고 Designer분, 의견 어떠신가요?"
    valid_speakers = ["Host", "PM", "Designer", "TechLead"]
    prompt = f'다음 발언에서 언급하거나 의견을 요청하는 참여자를 추출하세요.\n발언: "{content}"\n선택 가능한 참여자: {", ".join(valid_speakers)}\n언급된 참여자 이름만 쉼표로 구분하여 출력 (없으면 "없음"):'

    start_time = time.time()
    try:
        response = await model.ainvoke(prompt)
        latency = time.time() - start_time
        mentions = [s.strip() for s in response.content.split(",") if s.strip() in valid_speakers]

        success = "PM" in mentions and "Designer" in mentions
        status = "[green]PASS[/green]" if success else "[red]FAIL[/red]"

        console.print(f"Result: {mentions} in {latency:.2f}s - {status}")
        results.append({"Test": "Mention Extraction", "Status": "PASS" if success else "FAIL", "Latency": f"{latency:.2f}s"})

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        results.append({"Test": "Mention Extraction", "Status": "ERROR", "Latency": "-"})

    # Summary Table
    table = Table(title=f"Benchmark Results: {model_name}")
    table.add_column("Test Case")
    table.add_column("Status")
    table.add_column("Latency")
    
    for res in results:
        table.add_row(res["Test"], res["Status"], res["Latency"])
        
    console.print(table)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="LLM Benchmark for TheTable")
    parser.add_argument("--model", type=str, default="gpt-4o-mini", help="Model name")
    parser.add_argument("--base-url", type=str, help="Custom Base URL")
    parser.add_argument("--api-key", type=str, help="API Key")

    args = parser.parse_args()

    asyncio.run(benchmark_model(args.model, args.base_url, args.api_key))
