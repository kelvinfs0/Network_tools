#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
实时带宽监控器 - 监控网络接口带宽使用情况

使用 psutil 获取网络流量数据，rich 实时刷新显示，支持告警阈值。
"""

import argparse
import sys
import time
from datetime import datetime

import psutil
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.live import Live
from rich.text import Text

console = Console()


def format_bytes(bytes_val: float) -> str:
    """格式化字节数为可读字符串"""
    for unit in ["B/s", "KB/s", "MB/s", "GB/s"]:
        if abs(bytes_val) < 1024.0:
            return f"{bytes_val:.2f} {unit}"
        bytes_val /= 1024.0
    return f"{bytes_val:.2f} TB/s"


def format_total(bytes_val: float) -> str:
    """格式化总流量"""
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if abs(bytes_val) < 1024.0:
            return f"{bytes_val:.2f} {unit}"
        bytes_val /= 1024.0
    return f"{bytes_val:.2f} PB"


def get_interface_stats(interface: str = None):
    """获取网络接口统计信息"""
    counters = psutil.net_io_counters(pernic=True)

    if interface:
        if interface not in counters:
            return None
        return {interface: counters[interface]}

    # 返回所有非 lo 接口
    return {name: stats for name, stats in counters.items() if name != "lo"}


def build_display(
    interfaces: dict, prev_stats: dict, interval: float, alerts: list, alert_threshold: float
) -> Table:
    """构建显示表格"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    table = Table(
        title=f"📡 实时带宽监控 | {now}",
        border_style="cyan",
        show_lines=True,
        title_style="bold",
    )
    table.add_column("接口", style="bold cyan", min_width=12)
    table.add_column("上传速率", style="yellow", justify="right")
    table.add_column("下载速率", style="green", justify="right")
    table.add_column("总上传", style="dim", justify="right")
    table.add_column("总下载", style="dim", justify="right")
    table.add_column("发送包", style="dim", justify="right")
    table.add_column("接收包", style="dim", justify="right")
    table.add_column("状态", justify="center")

    current_stats = {}
    for name, stats in interfaces.items():
        current_stats[name] = stats

        if name in prev_stats:
            prev = prev_stats[name]
            upload_speed = (stats.bytes_sent - prev.bytes_sent) / interval
            download_speed = (stats.bytes_recv - prev.bytes_recv) / interval
        else:
            upload_speed = 0
            download_speed = 0

        # 告警检查
        status = "[green]✅ 正常[/green]"
        if upload_speed > alert_threshold or download_speed > alert_threshold:
            status = "[red]⚠️ 告警[/red]"
            alerts.append(f"[{now}] {name}: 上行={format_bytes(upload_speed)}, 下行={format_bytes(download_speed)}")

        table.add_row(
            name,
            format_bytes(upload_speed),
            format_bytes(download_speed),
            format_total(stats.bytes_sent),
            format_total(stats.bytes_recv),
            f"{stats.packets_sent:,}",
            f"{stats.packets_recv:,}",
            status,
        )

    return table


def main():
    parser = argparse.ArgumentParser(
        description="实时带宽监控器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s                              # 监控所有接口
  %(prog)s -i eth0                      # 监控指定接口
  %(prog)s -i "eth0,Wi-Fi"              # 监控多个接口
  %(prog)s --threshold 10485760         # 10MB/s 告警阈值
  %(prog)s --interval 2                 # 每2秒刷新
  %(prog)s --duration 60                # 监控60秒
        """,
    )
    parser.add_argument("-i", "--interface", default=None, help="指定网络接口（逗号分隔多个）")
    parser.add_argument("--interval", type=float, default=1.0, help="刷新间隔秒数（默认: 1）")
    parser.add_argument("--threshold", type=float, default=10485760, help="告警阈值（字节/秒，默认: 10MB）")
    parser.add_argument("--duration", type=int, default=0, help="监控持续秒数（默认: 0，持续监控）")

    args = parser.parse_args()

    # 获取接口列表
    all_counters = psutil.net_io_counters(pernic=True)
    available = [name for name in all_counters if name != "lo"]

    if args.interface:
        interfaces = {}
        for name in args.interface.split(","):
            name = name.strip()
            if name in all_counters:
                interfaces[name] = name
            else:
                console.print(f"[red]错误: 接口 '{name}' 不存在[/red]")
                console.print(f"[yellow]可用接口: {', '.join(available)}[/yellow]")
                sys.exit(1)
    else:
        interfaces = {name: name for name in available}

    if not interfaces:
        console.print("[red]错误: 没有可用的网络接口[/red]")
        sys.exit(1)

    alert_names = ", ".join(interfaces.keys())
    console.print(Panel(
        f"[bold]监控接口:[/bold] {alert_names}\n"
        f"[bold]刷新间隔:[/bold] {args.interval}s\n"
        f"[bold]告警阈值:[/bold] {format_bytes(args.threshold)}/s\n"
        f"[bold]持续时间:[/bold] {'持续监控' if args.duration == 0 else f'{args.duration}s'}",
        title="[bold cyan]📡 带宽监控器[/bold cyan]",
        border_style="cyan",
    ))
    console.print("[dim]按 Ctrl+C 停止监控[/dim]\n")

    alerts = []
    prev_stats = {}
    start_time = time.time()

    try:
        with Live(console=console, refresh_per_second=1, screen=False) as live:
            while True:
                # 获取当前统计
                current = {}
                for name in interfaces:
                    current[name] = psutil.net_io_counters(pernic=True)[name]

                # 构建显示
                table = build_display(current, prev_stats, args.interval, alerts, args.threshold)
                live.update(table)

                prev_stats = current
                time.sleep(args.interval)

                # 检查持续时间
                if args.duration > 0 and (time.time() - start_time) >= args.duration:
                    break

    except KeyboardInterrupt:
        pass

    # 显示告警历史
    if alerts:
        console.print(f"\n[bold red]⚠️ 告警历史 (共 {len(alerts)} 条):[/bold red]")
        for alert in alerts[-10:]:  # 最多显示最近10条
            console.print(f"  {alert}")
    else:
        console.print("\n[green]✅ 监控期间未触发告警[/green]")

    console.print("[dim]监控已停止[/dim]")


if __name__ == "__main__":
    main()
