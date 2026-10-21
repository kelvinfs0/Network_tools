#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多线程端口扫描器 - 快速扫描目标主机的开放端口

使用 socket 和 concurrent.futures 实现多线程扫描，rich 美化输出。
"""

import argparse
import socket
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeElapsedColumn

console = Console()

# 常见端口服务映射
COMMON_PORTS = {
    21: "FTP", 22: "SSH", 23: "Telnet", 25: "SMTP", 53: "DNS",
    80: "HTTP", 110: "POP3", 143: "IMAP", 443: "HTTPS", 445: "SMB",
    993: "IMAPS", 995: "POP3S", 1433: "MSSQL", 1521: "Oracle",
    3306: "MySQL", 3389: "RDP", 5432: "PostgreSQL", 5900: "VNC",
    6379: "Redis", 8080: "HTTP-Proxy", 8443: "HTTPS-Alt", 9090: "WebConsole",
    27017: "MongoDB",
}


def scan_port(host: str, port: int, timeout: float) -> tuple:
    """扫描单个端口，返回 (端口, 状态, 服务名)"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(timeout)
            result = sock.connect_ex((host, port))
            if result == 0:
                service = COMMON_PORTS.get(port, "未知")
                try:
                    service = socket.getservbyport(port, "tcp")
                except OSError:
                    service = COMMON_PORTS.get(port, "未知")
                return port, "开放", service
            else:
                return port, "关闭", "-"
    except socket.timeout:
        return port, "过滤", "-"
    except OSError:
        return port, "错误", "-"


def parse_ports(port_str: str) -> list:
    """解析端口范围字符串，如 '80,443,8000-8100'"""
    ports = []
    for part in port_str.split(","):
        part = part.strip()
        if "-" in part:
            start, end = part.split("-", 1)
            ports.extend(range(int(start), int(end) + 1))
        else:
            ports.append(int(part))
    return sorted(set(ports))


def main():
    parser = argparse.ArgumentParser(
        description="多线程端口扫描器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s 192.168.1.1                        # 扫描常见端口
  %(prog)s 192.168.1.1 -p 80,443,8080         # 扫描指定端口
  %(prog)s 192.168.1.1 -p 1-1024 -t 200       # 扫描1-1024端口，200线程
  %(prog)s scanme.nmap.org -p 22,80,443       # 扫描域名
        """,
    )
    parser.add_argument("host", help="目标主机 IP 或域名")
    parser.add_argument("-p", "--ports", default=None, help="端口范围，如 '80,443,8000-8100'（默认扫描常见端口）")
    parser.add_argument("-t", "--threads", type=int, default=100, help="线程数（默认: 100）")
    parser.add_argument("--timeout", type=float, default=1.0, help="连接超时秒数（默认: 1.0）")
    parser.add_argument("--all", action="store_true", help="只显示开放端口")

    args = parser.parse_args()

    # 解析目标
    host = args.host
    try:
        resolved = socket.gethostbyname(host)
        if resolved != host:
            console.print(f"[cyan]域名 {host} 解析为: {resolved}[/cyan]")
        host = resolved
    except socket.gaierror:
        console.print(f"[red]错误: 无法解析主机 '{host}'[/red]")
        sys.exit(1)

    # 解析端口
    if args.ports:
        ports = parse_ports(args.ports)
    else:
        ports = list(COMMON_PORTS.keys())

    console.print(Panel(
        f"[bold]目标:[/bold] {args.host} ({host})\n"
        f"[bold]端口数:[/bold] {len(ports)}\n"
        f"[bold]线程数:[/bold] {args.threads}\n"
        f"[bold]超时:[/bold] {args.timeout}s",
        title="[bold cyan]🔍 端口扫描器[/bold cyan]",
        border_style="cyan",
    ))

    open_ports = []
    closed_count = 0
    filtered_count = 0

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("扫描中...", total=len(ports))

        with ThreadPoolExecutor(max_workers=args.threads) as executor:
            futures = {executor.submit(scan_port, host, port, args.timeout): port for port in ports}
            for future in as_completed(futures):
                port, status, service = future.result()
                if status == "开放":
                    open_ports.append((port, status, service))
                elif status == "关闭":
                    closed_count += 1
                else:
                    filtered_count += 1
                progress.advance(task)

    # 结果表格
    if open_ports:
        table = Table(title="扫描结果", border_style="green", show_lines=True)
        table.add_column("端口", style="bold cyan", justify="center")
        table.add_column("状态", style="bold green", justify="center")
        table.add_column("服务", style="yellow")

        for port, status, service in sorted(open_ports):
            table.add_row(str(port), f"✅ {status}", service)

        console.print(table)
    else:
        console.print("[yellow]未发现开放端口[/yellow]")

    # 统计信息
    console.print(Panel(
        f"[green]开放: {len(open_ports)}[/green] | "
        f"[red]关闭: {closed_count}[/red] | "
        f"[yellow]过滤: {filtered_count}[/yellow] | "
        f"[cyan]总计: {len(ports)}[/cyan]",
        title="[bold]📊 扫描统计[/bold]",
        border_style="blue",
    ))


if __name__ == "__main__":
    main()
