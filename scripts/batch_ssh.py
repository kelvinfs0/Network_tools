#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量 SSH 命令执行器 - 在多台设备上并发执行 SSH 命令

读取 devices.yaml 设备清单，使用 paramiko 并发执行命令。
"""

import argparse
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import paramiko
import yaml
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn

console = Console()


def load_devices(config_path: str) -> list:
    """从 YAML 文件加载设备列表"""
    path = Path(config_path)
    if not path.exists():
        console.print(f"[red]错误: 配置文件 '{config_path}' 不存在[/red]")
        sys.exit(1)

    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    devices = data.get("devices", [])
    if not devices:
        console.print("[red]错误: 设备列表为空[/red]")
        sys.exit(1)

    return devices


def ssh_execute(device: dict, commands: list, timeout: int = 10) -> tuple:
    """
    SSH 连接设备并执行命令列表。
    返回 (设备名, 主机, 成功/失败, 结果字典或错误信息)
    """
    name = device.get("name", "未知")
    host = device.get("host", "")
    port = device.get("port", 22)
    username = device.get("username", "")
    password = device.get("password", "")
    secret = device.get("secret", "")  # enable 密码

    results = {}
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(
            hostname=host,
            port=port,
            username=username,
            password=password,
            timeout=timeout,
            look_for_keys=False,
            allow_agent=False,
        )

        # 如果有 enable 密码
        if secret:
            shell = client.invoke_shell()
            time.sleep(1)
            shell.recv(65535)
            shell.send("enable\n")
            time.sleep(1)
            shell.recv(65535)
            shell.send(f"{secret}\n")
            time.sleep(1)
            shell.recv(65535)

            for cmd in commands:
                shell.send(f"{cmd}\n")
                time.sleep(2)
                output = shell.recv(65535).decode("utf-8", errors="ignore")
                results[cmd] = output.strip()
            shell.close()
        else:
            for cmd in commands:
                stdin, stdout, stderr = client.exec_command(cmd, timeout=timeout)
                output = stdout.read().decode("utf-8", errors="ignore")
                error = stderr.read().decode("utf-8", errors="ignore")
                results[cmd] = output.strip() if output.strip() else error.strip()

        client.close()
        return name, host, True, results

    except paramiko.AuthenticationException:
        return name, host, False, "认证失败"
    except paramiko.SSHException as e:
        return name, host, False, f"SSH 错误: {e}"
    except Exception as e:
        return name, host, False, f"连接错误: {e}"


def main():
    parser = argparse.ArgumentParser(
        description="批量 SSH 命令执行器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s configs/devices.yaml -c "show version"              # 单条命令
  %(prog)s configs/devices.yaml -c "show ip int brief" -c "show version"  # 多条命令
  %(prog)s configs/devices.yaml -c "show version" -t 20        # 20秒超时
  %(prog)s configs/devices.yaml --filter "核心" -c "show clock" # 按名称过滤设备
        """,
    )
    parser.add_argument("config", help="设备配置文件路径 (YAML)")
    parser.add_argument("-c", "--command", action="append", required=True, help="要执行的命令（可多次指定）")
    parser.add_argument("-t", "--timeout", type=int, default=10, help="SSH 连接超时秒数（默认: 10）")
    parser.add_argument("--filter", default=None, help="按设备名称关键字过滤")
    parser.add_argument("--threads", type=int, default=10, help="并发线程数（默认: 10）")
    parser.add_argument("-o", "--output", default=None, help="结果输出到文件")

    args = parser.parse_args()

    devices = load_devices(args.config)

    # 过滤设备
    if args.filter:
        devices = [d for d in devices if args.filter.lower() in d.get("name", "").lower()]
        if not devices:
            console.print(f"[yellow]警告: 未找到匹配 '{args.filter}' 的设备[/yellow]")
            sys.exit(0)

    console.print(Panel(
        f"[bold]设备数:[/bold] {len(devices)}\n"
        f"[bold]命令数:[/bold] {len(args.command)}\n"
        f"[bold]并发数:[/bold] {args.threads}\n"
        f"[bold]超时:[/bold] {args.timeout}s",
        title="[bold cyan]🔗 批量 SSH 执行器[/bold cyan]",
        border_style="cyan",
    ))

    # 显示执行的命令
    console.print("[bold]执行命令:[/bold]")
    for cmd in args.command:
        console.print(f"  • {cmd}")
    console.print()

    results = []

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        console=console,
    ) as progress:
        task = progress.add_task("执行中...", total=len(devices))

        with ThreadPoolExecutor(max_workers=args.threads) as executor:
            futures = {
                executor.submit(ssh_execute, device, args.command, args.timeout): device
                for device in devices
            }
            for future in as_completed(futures):
                results.append(future.result())
                progress.advance(task)

    # 结果展示
    success_count = 0
    fail_count = 0
    output_lines = []

    for name, host, success, data in sorted(results, key=lambda x: x[0]):
        if success:
            success_count += 1
            table = Table(title=f"✅ {name} ({host})", border_style="green", show_lines=True)
            table.add_column("命令", style="cyan", min_width=20)
            table.add_column("输出", style="white")
            for cmd, output in data.items():
                # 截断过长输出
                display = output[:500] + "..." if len(output) > 500 else output
                table.add_row(cmd, display)
                output_lines.append(f"=== {name} ({host}) - {cmd} ===\n{output}\n")
            console.print(table)
        else:
            fail_count += 1
            console.print(Panel(
                f"[red]{data}[/red]",
                title=f"[red]❌ {name} ({host})[/red]",
                border_style="red",
            ))
            output_lines.append(f"=== {name} ({host}) - 失败: {data} ===\n")

    # 统计
    console.print(Panel(
        f"[green]成功: {success_count}[/green] | "
        f"[red]失败: {fail_count}[/red] | "
        f"[cyan]总计: {len(results)}[/cyan]",
        title="[bold]📊 执行统计[/bold]",
        border_style="blue",
    ))

    # 输出到文件
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write("\n".join(output_lines))
        console.print(f"[green]结果已保存到: {args.output}[/green]")


if __name__ == "__main__":
    main()
