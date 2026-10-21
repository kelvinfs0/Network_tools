#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量 DNS 解析器 - 批量解析域名并支持 DNS 服务器对比

从文件读取域名列表，对比不同 DNS 服务器的解析结果。
"""

import argparse
import socket
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import dns.resolver
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()


def resolve_domain(domain: str, dns_server: str = None, record_type: str = "A", timeout: float = 5.0) -> tuple:
    """
    解析单个域名。
    返回 (域名, 记录类型, 结果列表, 耗时ms, 错误信息)
    """
    start = time.time()
    try:
        resolver = dns.resolver.Resolver()
        resolver.timeout = timeout
        resolver.lifetime = timeout
        if dns_server:
            resolver.nameservers = [dns_server]

        answers = resolver.resolve(domain, record_type)
        elapsed = (time.time() - start) * 1000

        results = []
        for rdata in answers:
            results.append(str(rdata))

        return domain, record_type, results, f"{elapsed:.0f}ms", None
    except dns.resolver.NXDOMAIN:
        elapsed = (time.time() - start) * 1000
        return domain, record_type, [], f"{elapsed:.0f}ms", "域名不存在"
    except dns.resolver.NoAnswer:
        elapsed = (time.time() - start) * 1000
        return domain, record_type, [], f"{elapsed:.0f}ms", "无记录"
    except dns.resolver.NoNameservers:
        elapsed = (time.time() - start) * 1000
        return domain, record_type, [], f"{elapsed:.0f}ms", "无可用DNS"
    except dns.exception.Timeout:
        elapsed = (time.time() - start) * 1000
        return domain, record_type, [], f"{elapsed:.0f}ms", "超时"
    except Exception as e:
        elapsed = (time.time() - start) * 1000
        return domain, record_type, [], f"{elapsed:.0f}ms", str(e)[:50]


def load_domains(source: str) -> list:
    """从文件或逗号分隔字符串加载域名列表"""
    path = Path(source)
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return [line.strip() for line in f if line.strip() and not line.startswith("#")]
    else:
        return [d.strip() for d in source.split(",") if d.strip()]


def compare_dns(domains: list, servers: list, record_type: str, timeout: float, threads: int):
    """对比多个 DNS 服务器的解析结果"""
    all_results = {}

    for server in servers:
        console.print(f"\n[bold cyan]正在查询 DNS 服务器: {server}[/bold cyan]")
        server_results = {}

        with ThreadPoolExecutor(max_workers=threads) as executor:
            futures = {
                executor.submit(resolve_domain, domain, server, record_type, timeout): domain
                for domain in domains
            }
            for future in as_completed(futures):
                domain, rtype, results, elapsed, error = future.result()
                if error:
                    server_results[domain] = f"❌ {error}"
                else:
                    server_results[domain] = ", ".join(results)

        all_results[server] = server_results

    # 对比表格
    table = Table(title="DNS 解析对比", border_style="green", show_lines=True)
    table.add_column("域名", style="cyan", min_width=20)
    for server in servers:
        table.add_column(f"DNS: {server}", style="yellow", min_width=15)

    # 标记差异
    for domain in domains:
        row = [domain]
        values = [all_results[s].get(domain, "N/A") for s in servers]
        is_same = len(set(values)) == 1

        for v in values:
            if is_same:
                row.append(f"[green]{v}[/green]")
            else:
                row.append(f"[red]{v}[/red]")
        table.add_row(*row)

    console.print(table)

    # 统计差异
    diff_count = sum(
        1 for domain in domains
        if len(set(all_results[s].get(domain, "") for s in servers)) > 1
    )
    console.print(Panel(
        f"[bold]总域名:[/bold] {len(domains)} | "
        f"[green]一致: {len(domains) - diff_count}[/green] | "
        f"[red]差异: {diff_count}[/red]",
        title="[bold]📊 对比统计[/bold]",
        border_style="blue",
    ))


def main():
    parser = argparse.ArgumentParser(
        description="批量 DNS 解析器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s domains.txt                                    # 从文件解析
  %(prog)s "google.com,baidu.com,github.com"              # 逗号分隔域名
  %(prog)s domains.txt --dns 8.8.8.8                      # 指定 DNS 服务器
  %(prog)s domains.txt --compare 8.8.8.8,114.114.114.114  # 对比两个 DNS
  %(prog)s domains.txt -t AAAA                            # 查询 AAAA 记录
        """,
    )
    parser.add_argument("domains", help="域名列表文件或逗号分隔的域名")
    parser.add_argument("--dns", default=None, help="指定 DNS 服务器")
    parser.add_argument("--compare", default=None, help="对比多个 DNS 服务器（逗号分隔）")
    parser.add_argument("-t", "--type", default="A", help="DNS 记录类型（默认: A）")
    parser.add_argument("--timeout", type=float, default=5.0, help="查询超时秒数（默认: 5）")
    parser.add_argument("--threads", type=int, default=20, help="并发线程数（默认: 20）")

    args = parser.parse_args()

    domains = load_domains(args.domains)
    if not domains:
        console.print("[red]错误: 没有要解析的域名[/red]")
        sys.exit(1)

    console.print(Panel(
        f"[bold]域名数:[/bold] {len(domains)}\n"
        f"[bold]记录类型:[/bold] {args.type}\n"
        f"[bold]超时:[/bold] {args.timeout}s",
        title="[bold cyan]🌐 DNS 批量解析器[/bold cyan]",
        border_style="cyan",
    ))

    # 对比模式
    if args.compare:
        servers = [s.strip() for s in args.compare.split(",")]
        compare_dns(domains, servers, args.type, args.timeout, args.threads)
        return

    # 普通解析模式
    dns_server = args.dns

    table = Table(title="DNS 解析结果", border_style="green", show_lines=True)
    table.add_column("域名", style="cyan", min_width=20)
    table.add_column("记录类型", style="yellow", justify="center")
    table.add_column("解析结果", style="green")
    table.add_column("耗时", style="magenta", justify="center")
    table.add_column("状态", justify="center")

    success = 0
    fail = 0

    with ThreadPoolExecutor(max_workers=args.threads) as executor:
        futures = {
            executor.submit(resolve_domain, domain, dns_server, args.type, args.timeout): domain
            for domain in domains
        }
        for future in as_completed(futures):
            domain, rtype, results, elapsed, error = future.result()
            if error:
                fail += 1
                table.add_row(domain, rtype, f"[red]{error}[/red]", elapsed, "[red]❌[/red]")
            else:
                success += 1
                table.add_row(domain, rtype, ", ".join(results), elapsed, "[green]✅[/green]")

    console.print(table)
    console.print(Panel(
        f"[green]成功: {success}[/green] | "
        f"[red]失败: {fail}[/red] | "
        f"[cyan]总计: {len(domains)}[/cyan]",
        title="[bold]📊 解析统计[/bold]",
        border_style="blue",
    ))


if __name__ == "__main__":
    main()
