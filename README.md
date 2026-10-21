### 网络运维工具集

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Rich](https://img.shields.io/badge/Rich-美化终端-orange.svg)](https://github.com/Textualize/rich)

---

## ✨ 功能特性

| 工具 | 脚本 | 功能说明 |
|------|------|----------|
| 🔍 端口扫描器 | `scripts/port_scanner.py` | 多线程端口扫描，支持端口范围，Rich 表格输出 |
| 🧮 子网计算器 | `scripts/subnet_calculator.py` | CIDR 计算、子网划分，支持 IPv4 |
| 🔗 批量 SSH | `scripts/batch_ssh.py` | 并发 SSH 命令执行，读取设备清单 |
| 💾 配置备份 | `scripts/config_backup.py` | Netmiko 批量备份网络设备配置 |
| 🌐 DNS 解析器 | `scripts/dns_resolver.py` | 批量 DNS 解析，支持 DNS 服务器对比 |
| 📡 带宽监控 | `scripts/bandwidth_monitor.py` | 实时带宽监控，阈值告警，Rich Live 显示 |

---


### 开始使用

```bash
# 🔍 端口扫描
python scripts/port_scanner.py 192.168.1.1 -p 22,80,443,8080

# 🧮 子网计算
python scripts/subnet_calculator.py 192.168.1.0/24
python scripts/subnet_calculator.py 10.0.0.0/8 -s 16

# 🔗 批量 SSH
python scripts/batch_ssh.py configs/devices.yaml -c "show version"

# 💾 配置备份
python scripts/config_backup.py configs/devices.yaml -d ./backups

# 🌐 DNS 解析
python scripts/dns_resolver.py "google.com,baidu.com,github.com"
python scripts/dns_resolver.py domains.txt --compare 8.8.8.8,114.114.114.114

# 📡 带宽监控
python scripts/bandwidth_monitor.py
python scripts/bandwidth_monitor.py -i eth0 --threshold 5242880
```

---

## 📖 详细使用说明

### 🔍 端口扫描器

```bash
# 扫描常见端口
python scripts/port_scanner.py 192.168.1.1

# 扫描指定端口范围
python scripts/port_scanner.py 192.168.1.1 -p 1-1024

# 200线程并发，2秒超时
python scripts/port_scanner.py 192.168.1.1 -p 1-65535 -t 200 --timeout 2
```

### 🧮 子网计算器

```bash
# 计算子网信息
python scripts/subnet_calculator.py 172.16.0.0/12

# 子网划分：将 /24 划分为 4 个 /26
python scripts/subnet_calculator.py 192.168.1.0/24 -s 26
```

### 🔗 批量 SSH

```bash
# 执行单条命令
python scripts/batch_ssh.py configs/devices.yaml -c "show ip int brief"

# 执行多条命令
python scripts/batch_ssh.py configs/devices.yaml -c "show version" -c "show clock"

# 按设备名称过滤
python scripts/batch_ssh.py configs/devices.yaml --filter "交换机" -c "display version"

# 结果输出到文件
python scripts/batch_ssh.py configs/devices.yaml -c "show version" -o result.txt
```

### 💾 配置备份

```bash
# 备份所有设备
python scripts/config_backup.py configs/devices.yaml

# 指定备份目录
python scripts/config_backup.py configs/devices.yaml -d /data/backups

# 过滤并备份
python scripts/config_backup.py configs/devices.yaml --filter "核心"
```

### 🌐 DNS 解析器

```bash
# 从文件批量解析
python scripts/dns_resolver.py domains.txt

# 指定 DNS 服务器
python scripts/dns_resolver.py domains.txt --dns 8.8.8.8

# 对比多个 DNS 服务器
python scripts/dns_resolver.py domains.txt --compare 8.8.8.8,114.114.114.114

# 查询 MX 记录
python scripts/dns_resolver.py "google.com" -t MX
```

### 📡 带宽监控

```bash
# 监控所有接口
python scripts/bandwidth_monitor.py

# 监控指定接口，5MB/s 告警
python scripts/bandwidth_monitor.py -i eth0 --threshold 5242880

# 监控 60 秒
python scripts/bandwidth_monitor.py --duration 60
```

---

## 📁 项目结构

```
netops-toolkit/
├── scripts/
│   ├── port_scanner.py        # 多线程端口扫描器
│   ├── subnet_calculator.py   # 子网计算器
│   ├── batch_ssh.py           # 批量 SSH 命令执行器
│   ├── config_backup.py       # 网络设备配置备份
│   ├── dns_resolver.py        # 批量 DNS 解析器
│   └── bandwidth_monitor.py   # 实时带宽监控器
├── configs/
│   └── devices.yaml           # 设备清单配置模板
├── requirements.txt           # Python 依赖
├── README.md                  # 项目说明文档
├── LICENSE                    # MIT 开源协议
└── .gitignore                 # Git 忽略规则
```

---

## ⚙️ 配置说明

编辑 `configs/devices.yaml` 添加你的网络设备：

```yaml
devices:
  - name: "核心路由器"
    host: "192.168.1.1"
    port: 22
    device_type: "cisco_ios"
    username: "admin"
    password: "your_password"
    secret: "enable_password"
```

支持的设备类型：`cisco_ios`、`cisco_xe`、`cisco_nxos`、`huawei`、`h3c`、`juniper`、`arista`、`linux`

> ⚠️ **安全提示**：建议将 `devices.yaml` 的文件权限设为 `600`，生产环境使用密钥认证。

---

## 📋 依赖说明

| 库 | 用途 |
|----|------|
| [rich](https://github.com/Textualize/rich) | 终端美化输出（表格、面板、进度条、实时刷新） |
| [paramiko](https://github.com/paramiko/paramiko) | SSH 客户端 |
| [netmiko](https://github.com/ktbyers/netmiko) | 网络设备 SSH 管理（基于 paramiko） |
| [PyYAML](https://pyyaml.org/) | YAML 配置解析 |
| [dnspython](https://www.dnspython.org/) | DNS 查询 |
| [psutil](https://github.com/giampaolo/psutil) | 系统/网络监控 |

---

## 📄 开源协议

本项目采用 [MIT License](LICENSE) 开源协议。
