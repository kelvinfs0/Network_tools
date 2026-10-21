#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
网络设备配置备份工具 - 使用 Netmiko 批量备份设备运行配置

支持 Cisco IOS、Huawei VRP 等多种设备类型。
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

import yaml
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn

console = Console()

# Netmiko 设备类型映射
DEVICE_TYPE_MAP = {
    "cisco_ios": "cisco_ios",
    "cisco_xe": "cisco_xe",
    "cisco_xr": "cisco_xr",
    "cisco_nxos": "cisco_nxos",
    "huawei": "huawei_vrpv8",
    "huawei_vrp": "huawei_vrpv8",
    "h3c": "hp_comware",
    "juniper": "juniper_junos",
    "arista": "arista_eos",
    "linux": "linux",
}


def load_devices(config_path: str) -> list:
    """从 YAML 文件加载设备列表"""
    path = Path(config_path)
    if not path.exists():
        console.print(f"[red]错误: 配置文件 '{config_path}' 不存在[/red]")
        sys.exit(1)

    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data.get("devices", [])


def backup_device(device: dict, backup_dir: Path, timeout: int = 30) -> tuple:
    """
    备份单台设备配置。
    返回 (设备名, 主机, 成功/失败, 消息)
    """
    try:
        from netmiko import ConnectHandler
    except ImportError:
        return device.get("name", ""), device.get("host", ""), False, "请安装 netmiko: pip install netmiko"

    name = device.get("name", "unknown")
    host = device.get("host", "")
    device_type = device.get("device_type", "cisco_ios")

    # 映射设备类型
    mapped_type = DEVICE_TYPE_MAP.get(device_type, device_type)

    conn_params = {
        "device_type": mapped_type,
        "host": host,
        "port": device.get("port", 22),
        "username": device.get("username", ""),
        "password": device.get("password", ""),
        "timeout": timeout,
    }

    secret = device.get("secret", "")
    if secret:
        conn_params["secret"] = secret

    try:
        conn = ConnectHandler(**conn_params)
        if secret:
            conn.enable()

        # 根据设备类型选择命令
        if "huawei" in mapped_type or "comware" in mapped_type:
            cmd = "display current-configuration"
        else:
            cmd = "show running-config"

        config = conn.send_command(cmd, read_timeout=60)
        conn.disconnect()

        # 保存文件
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{name}_{host}_{timestamp}.txt"
        filepath = backup_dir / filename
        filepath.write_text(config, encoding="utf-8")

        size_kb = len(config.encode("utf-8")) / 1024
        return name, host, True, f"已保存 ({size_kb:.1f} KB)"

    except Exception as e:
        return name, host, False, str(e)[:100]


def main():
    parser = argparse.ArgumentParser(
        description="网络设备配置备份工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s configs/devices.yaml                        # 备份所有设备
  %(prog)s configs/devices.yaml -d ./backups           # 指定备份目录
  %(prog)s configs/devices.yaml --filter "交换机"      # 按名称过滤
  %(prog)s configs/devices.yaml -t 60                  # 60秒超时
        """,
    )
    parser.add_argument("config", help="设备配置文件路径 (YAML)")
    parser.add_argument("-d", "--dir", default="./backups", help="备份文件保存目录（默认: ./backups）")
    parser.add_argument("-t", "--timeout", type=int, default=30, help="连接超时秒数（默认: 30）")
    parser.add_argument("--filter", default=None, help="按设备名称关键字过滤")
    parser.add_argument("--threads", type=int, default=5, help="并发线程数（默认: 5）")

    args = parser.parse_args()

    devices = load_devices(args.config)

    if args.filter:
        devices = [d for d in devices if args.filter.lower() in d.get("name", "").lower()]

    if not devices:
        console.print("[yellow]没有匹配的设备[/yellow]")
        sys.exit(0)

    # 创建备份目录
    backup_dir = Path(args.dir)
    backup_dir.mkdir(parents=True, exist_ok=True)

    console.print(Panel(
        f"[bold]设备数:[/bold] {len(devices)}\n"
        f"[bold]备份目录:[/bold] {backup_dir.resolve()}\n"
        f"[bold]并发数:[/bold] {args.threads}",
        title="[bold cyan]💾 配置备份工具[/bold cyan]",
        border_style="cyan",
    ))

    results = []

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        console=console,
    ) as progress:
        task = progress.add_task("备份中...", total=len(devices))

        with ThreadPoolExecutor(max_workers=args.threads) as executor:
            futures = {
                executor.submit(backup_device, device, backup_dir, args.timeout): device
                for device in devices
            }
            for future in as_completed(futures):
                results.append(future.result())
                progress.advance(task)

    # 结果表格
    table = Table(title="备份结果", border_style="green", show_lines=True)
    table.add_column("设备", style="cyan")
    table.add_column("主机", style="yellow")
    table.add_column("状态", justify="center")
    table.add_column("详情")

    success = 0
    for name, host, ok, msg in sorted(results, key=lambda x: x[0]):
        status = "[green]✅ 成功[/green]" if ok else "[red]❌ 失败[/red]"
        table.add_row(name, host, status, msg)
        if ok:
            success += 1

    console.print(table)
    console.print(Panel(
        f"[green]成功: {success}[/green] | "
        f"[red]失败: {len(results) - success}[/red] | "
        f"[cyan]总计: {len(results)}[/cyan]",
        title="[bold]📊 备份统计[/bold]",
        border_style="blue",
    ))


if __name__ == "__main__":
    main()
