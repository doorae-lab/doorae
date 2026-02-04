
import asyncio
import argparse
import sys
import time
from typing import List, Dict

from langchain_core.messages import HumanMessage, AIMessage
from langchain.chat_models import init_chat_model
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

# Add project root to path
import os
sys.path.append(os.getcwd())

from thetable.graph.agenda_manager import extract_agenda_updates
from thetable.graph.workflow import extract_mentions_llm
from thetable.config import get_settings

console = Console()

async def benchmark_model(model_name: str, provider: str, base_url: str = None, api_key: str = None):
    console.print(f"[bold blue]Starting benchmark for {model_name} ({provider})[/bold blue]")
    
    settings = get_settings()
    
    # Init Model
    try:
        kwargs = {
            "temperature": 0.0,
            "max_tokens": 1024,
        }
        if base_url:
            kwargs["base_url"] = base_url
        if api_key:
            kwargs["api_key"] = api_key
        elif provider == "openai":
            kwargs["api_key"] = settings.openai_api_key

        model = init_chat_model(
            model=model_name,
            model_provider=provider,
            **kwargs
        )
        console.print(f"✅ Model initialized: {model.__class__.__name__}")
    except Exception as e:
        console.print(f"[bold red]❌ Model initialization failed: {e}[/bold red]")
        return

    results = []

    # Test 1: Agenda Extraction
    console.print("\n[bold]Test 1: Agenda Extraction (Structured Output)[/bold]")
    sample_messages = [
        HumanMessage(content="회의 시작합시다. 오늘 안건은 1. 현황공유, 2. 이슈논의입니다."),
        AIMessage(content="네 알겠습니다. 현황공유부터 하시죠.", name="PM"),
        HumanMessage(content="좋습니다. 이슈논의는 내일로 미룹시다.", name="Host")
    ]
    current_items = []
    
    start_time = time.time()
    try:
        agenda_result = await extract_agenda_updates(model, sample_messages, current_items)
        latency = time.time() - start_time
        
        items = agenda_result.items
        success = len(items) >= 2 and items[1].status == "deferred"
        status = "[green]PASS[/green]" if success else "[red]FAIL[/red]"
        
        console.print(f"Result: {len(items)} items extracted in {latency:.2f}s - {status}")
        for item in items:
            console.print(f"  - {item.title} ({item.status})")
            
        results.append({"Test": "Agenda Extraction", "Status": "PASS" if success else "FAIL", "Latency": f"{latency:.2f}s"})
        
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        results.append({"Test": "Agenda Extraction", "Status": "ERROR", "Latency": "-"})

    # Test 2: Mention Extraction
    console.print("\n[bold]Test 2: Mention Extraction[/bold]")
    content = "PM님, 그리고 Designer분, 의견 어떠신가요?"
    valid_speakers = ["Host", "PM", "Designer", "TechLead"]
    
    start_time = time.time()
    try:
        mentions = await extract_mentions_llm(content, model, valid_speakers)
        latency = time.time() - start_time
        
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
    parser.add_argument("--provider", type=str, default="openai", help="Model provider (openai, anthropic, ollama, etc)")
    parser.add_argument("--base-url", type=str, help="Custom Base URL")
    parser.add_argument("--api-key", type=str, help="API Key")
    
    args = parser.parse_args()
    
    asyncio.run(benchmark_model(args.model, args.provider, args.base_url, args.api_key))
