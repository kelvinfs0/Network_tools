#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
子网计算器 - IP 地址和 CIDR 子网计算工具

支持 CIDR 表示法，计算网络地址、广播地址、可用主机数、子网掩码等。
支持子网划分功能。
"""

import argparse
import ipaddress
import sys

from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()


def calculate_subnet(ip_cidr: str):
    """计算子网信息"""
    try:
        network = ipaddress.ip_network(ip_cidr, strict=False)
    except ValueError as e:
        console.print(f"[red]错误: {e}[/red]")
        sys.exit(1)

    prefix = network.prefixlen
    total_hosts = network.num_addresses
    usable_hosts = max(total_hosts - 2, 0) if prefix < 31 else total_hosts

    # 第一个和最后一个可用主机
    hosts = list(network.hosts())
    first_host = str(hosts[0]) if hosts and prefix < 31 else "N/A"
    last_host = str(hosts[-1]) if hosts and prefix < 31 else "N/A"

    info = {
        "输入地址": ip_cidr,
        "网络地址": str(network.network_address),
        "广播地址": str(network.broadcast_address) if prefix < 31 else "N/A",
        "子网掩码": str(network.netmask),
        "通配符掩码": str(network.hostmask),
        "CIDR 前缀": f"/{prefix}",
        "IP 版本": f"IPv{network.version}",
        "总地址数": f"{total_hosts:,}",
        "可用主机数": f"{usable_hosts:,}",
        "第一个可用主机": first_host,
        "最后一个可用主机": last_host,
        "是否私有地址": "是" if network.is_private else "否",
    }

    table = Table(title=f"子网计算结果 - {ip_cidr}", border_style="cyan", show_lines=True)
    table.add_column("属性", style="bold yellow", min_width=18)
    table.add_column("值", style="green")

    for key, value in info.items():
        table.add_row(key, value)

    console.print(table)
    return network


def subnet_division(ip_cidr: str, new_prefix: int):
    """将网络划分为更小的子网"""
    try:
        network = ipaddress.ip_network(ip_cidr, strict=False)
    except ValueError as e:
        console.print(f"[red]错误: {e}[/red]")
        sys.exit(1)

    if new_prefix <= network.prefixlen:
        console.print(f"[red]错误: 新前缀 /{new_prefix} 必须大于原前缀 /{network.prefixlen}[/red]")
        sys.exit(1)

    if new_prefix > 30:
        console.print("[yellow]警告: 前缀大于 /30 的子网几乎没有可用主机[/yellow]")

    subnets = list(network.subnets(new_prefix=new_prefix))

    table = Table(
        title=f"子网划分: {ip_cidr} → /{new_prefix}（共 {len(subnets)} 个子网）",
        border_style="green", show_lines=True,
    )
    table.add_column("#", style="dim", justify="center", width=5)
    table.add_column("子网地址", style="cyan")
    table.add_column("掩码", style="yellow")
    table.add_column("主机范围", style="green")
    table.add_column("可用数", style="magenta", justify="center")

    for i, subnet in enumerate(subnets, 1):
        hosts = list(subnet.hosts())
        if hosts and new_prefix < 31:
            host_range = f"{hosts[0]} - {hosts[-1]}"
            usable = len(hosts)
        else:
            host_range = "N/A"
            usable = subnet.num_addresses
        table.add_row(
            str(i),
            str(subnet),
            str(subnet.netmask),
            host_range,
            str(usable),
        )

    console.print(table)
    console.print(Panel(
        f"[bold]原始网络:[/bold] {ip_cidr}\n"
        f"[bold]划分前缀:[/bold] /{new_prefix}\n"
        f"[bold]子网数量:[/bold] {len(subnets)}\n"
        f"[bold]每子网可用:[/bold] {max(subnet.num_addresses - 2, 0) if new_prefix < 31 else subnet.num_addresses:,}",
        title="[bold]📊 划分统计[/bold]",
        border_style="blue",
    ))


def main():
    parser = argparse.ArgumentParser(
        description="子网计算器 - IP 地址和 CIDR 子网计算工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s 192.168.1.0/24                    # 计算子网信息
  %(prog)s 10.0.0.0/16                       # 计算大网段信息
  %(prog)s 192.168.1.0/24 -s 26              # 将 /24 划分为 /26 子网
  %(prog)s 172.16.0.0/12 -s 16               # 将 /12 划分为 /16 子网
        """,
    )
    parser.add_argument("ip_cidr", help="IP 地址和 CIDR 前缀，如 192.168.1.0/24")
    parser.add_argument("-s", "--subnet", type=int, metavar="PREFIX", help="子网划分：指定新的 CIDR 前缀")

    args = parser.parse_args()

    if args.subnet:
        subnet_division(args.ip_cidr, args.subnet)
    else:
        calculate_subnet(args.ip_cidr)


if __name__ == "__main__":
    main()
