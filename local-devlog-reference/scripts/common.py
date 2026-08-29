"""common.py — client / server 共用的基础设施。

职责：UTF-8 流配置、日志、路径解析、命名管道地址与收发封装。
按模板 best-practices：用户可见输出用中文，日志与内部错误用英文。
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import time
from datetime import datetime
from multiprocessing.connection import Client
from pathlib import Path

SKILL_NAME = "local-devlog"
AUTHKEY = SKILL_NAME.encode("utf-8")

# 服务端状态机取值，client 与 server 必须共用同一套字面量
STATE_STARTING = "starting"
STATE_DOWNLOADING = "downloading"
STATE_LOADING = "loading"
STATE_RUNNING = "running"
STATE_ERROR = "error"

# 退出码约定（模板 best-practices 强制）
EXIT_OK = 0
EXIT_ERROR = 1          # 通用错误：参数错误、无权限、硬件不支持
EXIT_CONN = 2           # 管道连接 / 通信失败
EXIT_DOWNLOADING = 3    # 模型仍在下载，需要 --continue


# --------------------------------------------------------------------------
# UTF-8：不配置则 Windows 控制台下中文全部乱码，这是模板列出的头号坑
# --------------------------------------------------------------------------
def configure_stream_encoding(stream) -> None:
    reconfigure = getattr(stream, "reconfigure", None)
    if callable(reconfigure):
        try:
            reconfigure(encoding="utf-8")
        except Exception:
            # 某些被重定向的流不支持 reconfigure，忽略，不影响主流程
            pass


def configure_stdio() -> None:
    configure_stream_encoding(sys.stdout)
    configure_stream_encoding(sys.stderr)


# --------------------------------------------------------------------------
# 路径：全部基于用户主目录下的 .openvino，禁止相对路径
# --------------------------------------------------------------------------
def base_dir() -> Path:
    """宿主基础目录。Windows 下即 %USERPROFILE%\\.openvino。"""
    return Path(os.path.expanduser("~")) / ".openvino"


def log_dir() -> Path:
    d = base_dir() / "log"
    d.mkdir(parents=True, exist_ok=True)
    return d


def state_dir() -> Path:
    """本 skill 的状态目录，存挂起请求、ADR 序号等。"""
    d = base_dir() / SKILL_NAME
    d.mkdir(parents=True, exist_ok=True)
    return d


def runtime_dir() -> Path:
    """server 实际运行的脚本副本目录（热更新安全：不从安装目录直接跑）。"""
    d = base_dir() / "runtime" / SKILL_NAME
    d.mkdir(parents=True, exist_ok=True)
    return d


def models_dir() -> Path:
    d = base_dir() / "models"
    d.mkdir(parents=True, exist_ok=True)
    return d


def pending_file() -> Path:
    return state_dir() / "pending.json"


def skill_root() -> Path:
    """skill 安装根目录（scripts/ 的父目录）。"""
    return Path(__file__).resolve().parent.parent


def load_info() -> dict:
    """读取 info.json；找不到时抛出，交由调用方转成退出码 1。"""
    # server 从 runtime 副本运行时，info.json 不在其父目录，
    # 因此优先用环境变量传入的安装根目录。
    env_root = os.environ.get("LOCAL_DEVLOG_ROOT")
    candidates = []
    if env_root:
        candidates.append(Path(env_root) / "info.json")
    candidates.append(skill_root() / "info.json")

    for p in candidates:
        if p.is_file():
            with open(p, "r", encoding="utf-8") as fh:
                return json.load(fh)
    raise FileNotFoundError(f"info.json not found, tried: {[str(c) for c in candidates]}")


# --------------------------------------------------------------------------
# 日志：格式 [YYYY-MM-DD HH:MM:SS] [<role> pid=<PID>] <message>
# --------------------------------------------------------------------------
class Logger:
    def __init__(self, role: str) -> None:
        self.role = role
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        self.path = log_dir() / f"{SKILL_NAME}-{role}-{stamp}.log"

    def log(self, message: str) -> None:
        line = "[{ts}] [{role} pid={pid}] {msg}".format(
            ts=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            role=self.role,
            pid=os.getpid(),
            msg=message,
        )
        try:
            with open(self.path, "a", encoding="utf-8") as fh:
                fh.write(line + "\n")
        except Exception:
            # 日志失败绝不能影响主流程
            pass


# --------------------------------------------------------------------------
# 管道地址：Windows 用命名管道；其它平台回落 Unix socket。
# 回落不是为了跨平台发布（本 skill 面向 Windows AI PC），而是为了让协议逻辑
# 能在 CI / 非 Windows 机器上做端到端冒烟测试（模板 best-practices 第 8 条）。
# --------------------------------------------------------------------------
def pipe_address() -> str:
    if os.name == "nt":
        return rf"\\.\pipe\{SKILL_NAME}"
    return os.path.join(tempfile.gettempdir(), f"{SKILL_NAME}.sock")


def send(payload: dict, timeout: float = 300.0) -> dict:
    """向 server 发一条消息并等待应答。失败抛异常，由调用方转退出码 2。"""
    address = pipe_address()
    conn = Client(address, authkey=AUTHKEY)
    try:
        conn.send(payload)
        if conn.poll(timeout):
            return conn.recv()
        raise TimeoutError(f"no response within {timeout}s")
    finally:
        try:
            conn.close()
        except Exception:
            pass


def try_status(timeout: float = 10.0) -> dict | None:
    """探测 server 状态。未启动或不可达返回 None，不抛异常。"""
    try:
        return send({"op": "status"}, timeout=timeout)
    except Exception:
        return None


def now_ts() -> float:
    return time.time()
