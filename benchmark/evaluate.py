import os
import sys
import json
import time
from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

# Add project root to sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from ai_infra.llm_client import OllamaClient
from intelligence.analyzer import ConversationAnalyzer

console = Console()

def run_benchmark():
    dataset_path = os.path.join(BASE_DIR, "benchmark", "golden_dataset.json")
    if not os.path.exists(dataset_path):
        console.print(f"[bold red]Error: Golden dataset not found at {dataset_path}[/bold red]")
        return

    with open(dataset_path, "r", encoding="utf-8") as f:
        test_cases = json.load(f)

    client = OllamaClient()
    if not client.is_healthy():
        console.print("[bold red]Error: Ollama service is not reachable at http://127.0.0.1:11434[/bold red]")
        return

    analyzer = ConversationAnalyzer(model=client.llm_model, llm_client=client)

    console.print(Panel(
        f"[bold cyan]Local AI Voice Assistant - Prompt & Intelligence Benchmark[/bold cyan]\n"
        f"Model: [green]{client.llm_model}[/green] | Dataset Size: [yellow]{len(test_cases)} tests[/yellow]\n"
        f"Date: [dim]{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}[/dim]",
        border_style="cyan"
    ))

    table = Table(title="Test Case Evaluation Results", show_lines=True)
    table.add_column("ID", style="bold dim", width=16)
    table.add_column("Query Snippet", width=36)
    table.add_column("Intent", width=16)
    table.add_column("Web Search", width=12)
    table.add_column("RAG", width=8)
    table.add_column("Code", width=8)
    table.add_column("Time", justify="right", width=8)
    table.add_column("Status", justify="center", width=8)

    results = []
    total_checks = 0
    passed_checks = 0
    total_latency = 0.0

    intent_checks = 0
    intent_passed = 0
    web_checks = 0
    web_passed = 0
    rag_checks = 0
    rag_passed = 0
    code_checks = 0
    code_passed = 0

    with console.status("[bold green]Evaluating benchmark test cases against local model...[/bold green]"):
        for case in test_cases:
            cid = case["id"]
            query = case["query"]
            expected = case["expected"]

            t0 = time.time()
            analysis = analyzer.analyze_sync(query)
            elapsed = round(time.time() - t0, 3)
            total_latency += elapsed

            case_passed = True
            checks_in_case = 0
            checks_passed_in_case = 0

            # 1. Intent check
            intent_str = f"{analysis.intent}"
            if "intent" in expected:
                intent_checks += 1
                checks_in_case += 1
                if analysis.intent == expected["intent"]:
                    intent_passed += 1
                    checks_passed_in_case += 1
                    intent_str = f"[green]{analysis.intent}[/green]"
                else:
                    case_passed = False
                    intent_str = f"[red]{analysis.intent}[/red]\n[dim](exp: {expected['intent']})[/dim]"

            # 2. Web search check
            web_str = str(analysis.needs_web_search)
            if "needs_web_search" in expected:
                web_checks += 1
                checks_in_case += 1
                if analysis.needs_web_search == expected["needs_web_search"]:
                    web_passed += 1
                    checks_passed_in_case += 1
                    web_str = f"[green]{analysis.needs_web_search}[/green]"
                else:
                    case_passed = False
                    web_str = f"[red]{analysis.needs_web_search}[/red]\n[dim](exp: {expected['needs_web_search']})[/dim]"

            # 3. RAG check
            rag_str = str(analysis.needs_rag)
            if "needs_rag" in expected:
                rag_checks += 1
                checks_in_case += 1
                if analysis.needs_rag == expected["needs_rag"]:
                    rag_passed += 1
                    checks_passed_in_case += 1
                    rag_str = f"[green]{analysis.needs_rag}[/green]"
                else:
                    case_passed = False
                    rag_str = f"[red]{analysis.needs_rag}[/red]\n[dim](exp: {expected['needs_rag']})[/dim]"

            # 4. Code check
            code_str = str(analysis.needs_code)
            if "needs_code" in expected:
                code_checks += 1
                checks_in_case += 1
                if analysis.needs_code == expected["needs_code"]:
                    code_passed += 1
                    checks_passed_in_case += 1
                    code_str = f"[green]{analysis.needs_code}[/green]"
                else:
                    case_passed = False
                    code_str = f"[red]{analysis.needs_code}[/red]\n[dim](exp: {expected['needs_code']})[/dim]"

            total_checks += checks_in_case
            passed_checks += checks_passed_in_case

            status_str = "[bold green]PASS[/bold green]" if case_passed else "[bold red]FAIL[/bold red]"
            snippet = (query[:33] + "...") if len(query) > 36 else query
            table.add_row(cid, snippet, intent_str, web_str, rag_str, code_str, f"{elapsed}s", status_str)

            results.append({
                "id": cid,
                "query": query,
                "passed": case_passed,
                "latency_seconds": elapsed,
                "expected": expected,
                "actual": analysis.model_dump()
            })

    console.print(table)

    # Summary Statistics
    avg_latency = round(total_latency / len(test_cases), 3) if test_cases else 0.0
    overall_accuracy = round((passed_checks / total_checks) * 100, 1) if total_checks else 0.0
    intent_acc = round((intent_passed / intent_checks) * 100, 1) if intent_checks else 0.0
    web_acc = round((web_passed / web_checks) * 100, 1) if web_checks else 0.0
    rag_acc = round((rag_passed / rag_checks) * 100, 1) if rag_checks else 0.0
    code_acc = round((code_passed / code_checks) * 100, 1) if code_checks else 0.0

    summary_table = Table(title="Overall Benchmark Summary", show_header=True)
    summary_table.add_column("Dimension", style="bold")
    summary_table.add_column("Score", justify="right")
    summary_table.add_column("Evaluated Checks", justify="right")

    summary_table.add_row("Intent Classification", f"[cyan]{intent_acc}%[/cyan]", f"{intent_passed}/{intent_checks}")
    summary_table.add_row("Web Search Routing", f"[cyan]{web_acc}%[/cyan]", f"{web_passed}/{web_checks}")
    summary_table.add_row("Document RAG Routing", f"[cyan]{rag_acc}%[/cyan]", f"{rag_passed}/{rag_checks}")
    summary_table.add_row("Code Need Detection", f"[cyan]{code_acc}%[/cyan]", f"{code_passed}/{code_checks}")
    summary_table.add_row("[bold]Overall Ground-Truth Accuracy[/bold]", f"[bold green]{overall_accuracy}%[/bold green]", f"{passed_checks}/{total_checks}")
    summary_table.add_row("Average Analyzer Latency", f"[yellow]{avg_latency}s[/yellow]", f"{len(test_cases)} queries")

    console.print(summary_table)

    # Save run results
    results_dir = os.path.join(BASE_DIR, "benchmark", "results")
    run_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_file = os.path.join(results_dir, f"run_{run_timestamp}.json")
    latest_file = os.path.join(results_dir, "latest_run.json")

    run_data = {
        "timestamp": run_timestamp,
        "model": client.llm_model,
        "overall_accuracy_percent": overall_accuracy,
        "intent_accuracy_percent": intent_acc,
        "web_search_accuracy_percent": web_acc,
        "rag_accuracy_percent": rag_acc,
        "code_accuracy_percent": code_acc,
        "average_latency_seconds": avg_latency,
        "cases": results
    }

    with open(run_file, "w", encoding="utf-8") as f:
        json.dump(run_data, f, indent=2)
    with open(latest_file, "w", encoding="utf-8") as f:
        json.dump(run_data, f, indent=2)

    console.print(f"\n[dim]Run metrics saved to: benchmark/results/run_{run_timestamp}.json[/dim]\n")

if __name__ == "__main__":
    run_benchmark()

