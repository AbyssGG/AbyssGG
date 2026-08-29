"""server.py — 长生命周期模型服务。

监听命名管道，后台线程下载并加载模型，模型常驻内存，服务
status / ensure_model / request / shutdown 四种操作。

状态机：starting → downloading → loading → running（失败进 error）

本进程完全不接触用户仓库：证据采集与文件写入都在 client 侧完成，
server 只收结构化证据包并做模型推理。
"""
from __future__ import annotations

import os
import shutil
import sys
import threading
import time
import traceback
from multiprocessing.connection import Listener
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import common  # noqa: E402
from common import (  # noqa: E402
    STATE_DOWNLOADING,
    STATE_ERROR,
    STATE_LOADING,
    STATE_RUNNING,
    STATE_STARTING,
)

common.configure_stdio()

LOG = common.Logger("server-py")

# 模型档位 → 魔搭仓库 ID。两者都是 INT4 OpenVINO IR。
TIERS = {
    "1.5b": {
        "model_id": "OpenVINO/Qwen2.5-Coder-1.5B-Instruct-int4-ov",
        "dir_name": "Qwen2.5-Coder-1.5B-Instruct-int4-ov",
        "approx_mib": 898,
    },
    "7b": {
        "model_id": "OpenVINO/Qwen2.5-Coder-7B-Instruct-int4-ov",
        "dir_name": "Qwen2.5-Coder-7B-Instruct-int4-ov",
        "approx_mib": 4300,
    },
}

DEFAULT_TIER = "1.5b"
IDLE_SHUTDOWN_GRACE = 30.0   # 超过保活时限后再多等这么久才真正退出


# ==========================================================================
# 模型下载：.partial 目录 + required_files 校验 + 原子替换
# 直接下到最终目录是模板点名的坑：中断后留下不完整目录，下次会被误判为完整。
# ==========================================================================
def _dir_size(path: Path) -> int:
    total = 0
    if not path.exists():
        return 0
    for root, _dirs, files in os.walk(path):
        for name in files:
            try:
                total += (Path(root) / name).stat().st_size
            except OSError:
                pass
    return total


def _query_total_bytes(model_id: str) -> int:
    """向魔搭查询仓库文件总大小，用于计算下载进度。失败返回 0。"""
    import json
    import urllib.request

    url = (f"https://www.modelscope.cn/api/v1/models/{model_id}"
           f"/repo/files?Revision=master&Root=")
    try:
        with urllib.request.urlopen(url, timeout=20) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        files = (data.get("Data") or {}).get("Files") or []
        return sum(int(f.get("Size") or 0) for f in files)
    except Exception as exc:
        LOG.log(f"query total bytes failed: {exc}")
        return 0


def is_model_complete(final: Path, required_files: list[str]) -> bool:
    return final.is_dir() and all((final / f).is_file() for f in required_files)


def download_model(tier_cfg: dict, required_files: list[str],
                   progress_setter) -> Path:
    """下载模型到 models 目录，返回最终目录。已完整则直接返回。"""
    dest_root = common.models_dir()
    final = dest_root / tier_cfg["dir_name"]

    if is_model_complete(final, required_files):
        LOG.log(f"model already complete at {final}")
        return final

    partial = dest_root / (tier_cfg["dir_name"] + ".partial")
    partial.mkdir(parents=True, exist_ok=True)

    total = _query_total_bytes(tier_cfg["model_id"])
    if total <= 0:
        total = int(tier_cfg["approx_mib"] * 1024 * 1024)
    LOG.log(f"downloading {tier_cfg['model_id']} -> {partial}, total={total}")

    # 监控线程只读目录大小，不参与下载，退出由 stop 事件控制
    stop = threading.Event()

    def monitor() -> None:
        while not stop.is_set():
            done = _dir_size(partial)
            pct = min(99.0, done * 100.0 / total) if total else 0.0
            progress_setter(pct)
            stop.wait(2.0)

    mon = threading.Thread(target=monitor, daemon=True)
    mon.start()

    try:
        from modelscope import snapshot_download
        # local_dir 指向 .partial：中断后残留物不会被误判为完整模型，
        # modelscope 自身的续传能力在此目录内继续生效。
        snapshot_download(tier_cfg["model_id"], local_dir=str(partial))
    finally:
        stop.set()

    missing = [f for f in required_files if not (partial / f).is_file()]
    if missing:
        raise RuntimeError(f"download incomplete, missing: {missing}")

    # 原子替换：先挪走旧目录再重命名，避免半更新状态
    if final.exists():
        stale = dest_root / (tier_cfg["dir_name"] + f".stale-{int(time.time())}")
        final.rename(stale)
        shutil.rmtree(stale, ignore_errors=True)
    partial.rename(final)
    progress_setter(100.0)
    LOG.log(f"model ready at {final}")
    return final


# ==========================================================================
# 服务实现
# ==========================================================================
class Server:
    def __init__(self, info: dict) -> None:
        self.info = info
        self.state = STATE_STARTING
        self.error = ""
        self.progress = 0.0
        self.started_at = time.time()
        self.last_active = time.time()

        self.backend = None
        self.tier = DEFAULT_TIER
        self.device = ""
        self.model_name = ""

        self._lock = threading.Lock()
        self._thread: threading.Thread | None = None

        alive = info.get("server_alive_timeout", 300)
        self.alive_timeout = None if alive == -1 else float(alive)

    # ---------------- 加载 ----------------
    def start_load(self, tier: str) -> None:
        """启动（或重启）后台加载线程。调用方需已持锁或确保无竞争。"""
        if self._thread and self._thread.is_alive():
            LOG.log("load thread already running, ignore")
            return
        self.tier = tier
        self.state = STATE_DOWNLOADING
        self.progress = 0.0
        self.error = ""
        self._thread = threading.Thread(target=self._load, args=(tier,), daemon=True)
        self._thread.start()

    def _set_progress(self, pct: float) -> None:
        self.progress = pct

    def _load(self, tier: str) -> None:
        """按后端优先级加载。

        关键：只有 openvino-genai 路径才需要本 skill 自己下载模型权重。
        Isvik 拥有自己的模型库（isvik -import 管理），重复下载 0.9 GiB 纯属浪费；
        规则降级路径根本不需要模型。因此下载被推迟到确认要走 genai 时才执行。
        """
        try:
            import backends
            tier_cfg = TIERS[tier]
            forced = (os.environ.get(backends.ENV_FORCE_BACKEND) or "").strip().lower()

            def _adopt(backend, model_label: str) -> None:
                old = self.backend
                self.backend = backend
                if old is not None and old is not backend:
                    try:
                        old.close()
                    except Exception:
                        pass
                self.device = backend.device
                self.model_name = model_label
                self.state = STATE_RUNNING
                LOG.log(f"running: backend={backend.name} device={backend.device} "
                        f"model={model_label}")

            # --- 规则降级：不需要任何模型 ---
            if forced == "rule":
                self.state = STATE_LOADING
                _adopt(backends.RuleBackend(reason="由环境变量强制指定"), "(无模型)")
                return

            # --- Isvik：模型由 Isvik 自己管理，跳过下载 ---
            if forced in ("", "isvik"):
                ok, detail = backends.IsvikBackend.probe()
                LOG.log(f"isvik probe: ok={ok} {detail}")
                if ok:
                    self.state = STATE_LOADING
                    try:
                        be = backends.IsvikBackend(
                            model_id=tier_cfg["model_id"], log=LOG)
                        _adopt(be, be.model or tier_cfg["dir_name"])
                        return
                    except Exception as exc:
                        LOG.log(f"isvik backend init failed, will try genai: {exc}")
                elif forced == "isvik":
                    raise RuntimeError(f"Isvik 后端被强制指定但不可用：{detail}")

            # --- openvino-genai：需要本地权重，此时才下载 ---
            ok, detail = backends.GenAIBackend.probe()
            if not ok:
                LOG.log(f"genai unavailable: {detail}")
                self.state = STATE_LOADING
                _adopt(backends.RuleBackend(reason=detail), "(无模型)")
                return

            required = self._required_files_for(tier_cfg["dir_name"])
            self.state = STATE_DOWNLOADING
            model_dir = download_model(tier_cfg, required, self._set_progress)

            self.state = STATE_LOADING
            LOG.log(f"loading genai backend from {model_dir}")
            _adopt(backends.GenAIBackend(model_dir=model_dir, log=LOG),
                   tier_cfg["dir_name"])
        except Exception:
            self.error = traceback.format_exc()
            self.state = STATE_ERROR
            LOG.log(f"load failed: {self.error[:800]}")

    def _required_files_for(self, dir_name: str) -> list[str]:
        """从 info.json 取 required_files；档位不在 info.json 中时用通用集合。"""
        for m in self.info.get("models", []):
            if m.get("dir_name") == dir_name:
                return list(m.get("required_files") or [])
        return ["config.json", "openvino_model.xml", "openvino_model.bin"]

    # ---------------- 协议 ----------------
    def handle(self, msg: dict) -> dict:
        op = msg.get("op")
        self.last_active = time.time()

        if op == "status":
            return {
                "ok": True,
                "state": self.state,
                "pid": os.getpid(),
                "uptime_s": time.time() - self.started_at,
                "progress": round(self.progress, 1),
                "tier": self.tier,
                "backend": getattr(self.backend, "name", ""),
                "device": self.device,
                "model": self.model_name,
                "error": self.error,
            }

        if op == "ensure_model":
            want = (msg.get("tier") or DEFAULT_TIER).lower()
            if want not in TIERS:
                return {"ok": False, "error": f"unknown model tier: {want}"}
            with self._lock:
                if want != self.tier or self.state == STATE_ERROR:
                    LOG.log(f"switching tier {self.tier} -> {want}")
                    self.start_load(want)
                    return {"ok": True, "switching": True, "tier": want}
                if self.state == STATE_STARTING:
                    self.start_load(want)
                    return {"ok": True, "switching": True, "tier": want}
            return {"ok": True, "switching": False, "tier": self.tier}

        if op == "request":
            if self.state != STATE_RUNNING:
                return {"ok": False, "error": f"not ready: {self.state}"}
            try:
                import devlog_engine
                fields = devlog_engine.extract_fields(
                    evidence=msg.get("evidence") or {},
                    intent=msg.get("intent") or "",
                    rejected=msg.get("rejected") or [],
                    backend=self.backend,
                    log=LOG,
                )
                return {
                    "ok": True,
                    "fields": fields,
                    "backend": self.backend.name,
                    "device": self.device,
                    "model": self.model_name,
                }
            except Exception as exc:
                LOG.log(f"request failed: {traceback.format_exc()[:800]}")
                return {"ok": False, "error": str(exc)}

        if op == "shutdown":
            return {"ok": True, "state": "shutting_down"}

        return {"ok": False, "error": f"unknown op: {op}"}

    # ---------------- 保活 ----------------
    def expired(self) -> bool:
        if self.alive_timeout is None:
            return False
        idle = time.time() - self.last_active
        return idle > (self.alive_timeout + IDLE_SHUTDOWN_GRACE)


def _cleanup_stale_socket(address: str) -> None:
    """非 Windows 下 Unix socket 残留会导致 Listener 绑定失败。"""
    if os.name != "nt" and os.path.exists(address):
        try:
            os.unlink(address)
        except OSError:
            pass


def main() -> int:
    try:
        info = common.load_info()
    except Exception as exc:
        LOG.log(f"cannot load info.json: {exc}")
        return 1

    srv = Server(info)
    srv.start_load(DEFAULT_TIER)

    address = common.pipe_address()
    _cleanup_stale_socket(address)

    LOG.log(f"listening on {address}")
    try:
        with Listener(address, authkey=common.AUTHKEY) as listener:
            while True:
                # 设超时以便定期检查保活过期
                try:
                    conn = listener.accept()
                except Exception as exc:
                    LOG.log(f"accept failed: {exc}")
                    break

                with conn:
                    try:
                        msg = conn.recv()
                    except Exception as exc:
                        LOG.log(f"recv failed: {exc}")
                        continue

                    resp = srv.handle(msg)
                    try:
                        conn.send(resp)
                    except Exception as exc:
                        LOG.log(f"send failed: {exc}")

                    if msg.get("op") == "shutdown":
                        LOG.log("shutdown requested, exiting")
                        if srv.backend is not None:
                            try:
                                srv.backend.close()
                            except Exception:
                                pass
                        return 0
    finally:
        _cleanup_stale_socket(address)
    return 0


if __name__ == "__main__":
    sys.exit(main())
