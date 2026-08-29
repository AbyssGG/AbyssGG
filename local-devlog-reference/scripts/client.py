"""client.py — 短生命周期客户端。

流程：参数解析 → 硬件门禁 → 同步运行时副本 → 确保 server 就绪 →
本地采集证据 → 送 server 抽取 → 渲染 ADR → 追加落盘。

设计要点：git 证据采集与文件写入都在 client 侧完成。
原因：server 是常驻进程，其工作目录不是用户的仓库；client 由 host 在
用户仓库的 cwd 下启动，只有它能看到正确的仓库上下文。
server 因此完全不接触文件系统，只做模型推理。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import common  # noqa: E402
from common import (  # noqa: E402
    EXIT_CONN,
    EXIT_DOWNLOADING,
    EXIT_ERROR,
    EXIT_OK,
    STATE_DOWNLOADING,
    STATE_ERROR,
    STATE_LOADING,
    STATE_RUNNING,
)

common.configure_stdio()

LOG = common.Logger("client-py")

DOWNLOAD_WAIT_TIMEOUT = 8 * 60   # 超过此时长仍未就绪则保存挂起请求并提示 --continue
READY_POLL_INTERVAL = 1.5
ERROR_RETRY_MAX = 3              # server 进入 error 态后的重启次数上限
SPAWN_WAIT_TIMEOUT = 45          # 等待 server 建立管道的时长


# ==========================================================================
# 参数
# ==========================================================================
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="run.ps1",
        description="在本地英特尔 AI PC 上生成带证据锚点的工程决策记录（DEVLOG / ADR）",
        add_help=True,
    )
    p.add_argument("intent", nargs="?", default=None,
                   help="本次决策的一句话意图")
    p.add_argument("--commits", type=int, default=None,
                   help="分析最近 N 个提交；缺省分析工作区未提交变更")
    p.add_argument("--test-log", dest="test_log", default=None,
                   help="测试或 benchmark 输出文件，作为 Verified Facts 的证据来源")
    p.add_argument("--rejected", action="append", default=[],
                   help='显式登记被否方案，格式 "方案|理由"，可重复')
    p.add_argument("--out", default="DEVLOG.md", help="目标日志文件")
    p.add_argument("--dry-run", dest="dry_run", action="store_true",
                   help="只打印结果，不写文件")
    p.add_argument("--model", default=None,
                   help="模型档位：缺省 1.5b；传 7b 切质量优先档（大概率回落 CPU）")
    p.add_argument("--doctor", action="store_true",
                   help="打印后端与设备自检结果后退出")
    p.add_argument("--continue", dest="do_continue", action="store_true",
                   help="续传上次未完成的模型下载并执行挂起的请求")
    p.add_argument("--allow-non-intel", dest="allow_non_intel", action="store_true",
                   help="跳过 Intel 平台门禁（仅供在非目标硬件上做协议自测）")
    return p


# ==========================================================================
# 硬件门禁（第二道）
# run.ps1 中的 platform.exe 是宿主专有的 pre-Python 门禁；宿主未提供时
# 由这里用 OpenVINO 的设备枚举兜底。这也是 requirements 里 openvino
# 依赖的真实用途之一。
# ==========================================================================
def detect_devices() -> dict:
    try:
        import openvino as ov
    except Exception as exc:
        LOG.log(f"openvino import failed: {exc}")
        return {"__error__": str(exc)}

    result: dict = {}
    try:
        core = ov.Core()
        for dev in core.available_devices:
            try:
                result[dev] = core.get_property(dev, "FULL_DEVICE_NAME")
            except Exception:
                result[dev] = "(name unavailable)"
        try:
            result["__version__"] = ov.get_version()
        except Exception:
            pass
    except Exception as exc:
        LOG.log(f"openvino core init failed: {exc}")
        return {"__error__": str(exc)}
    return result


def hardware_gate(devices: dict, allow_non_intel: bool) -> tuple[bool, str]:
    """返回 (是否放行, 面向用户的中文说明)。"""
    if "__error__" in devices:
        if allow_non_intel:
            # 允许在没有 OpenVINO 的机器上跑通协议链路，供 CI / 单测使用
            return True, ("警告：OpenVINO 不可用，已按 --allow-non-intel 继续，"
                          "仅能使用规则降级后端。")
        return False, (
            "OpenVINO 运行时不可用，无法枚举推理设备：\n"
            f"  {devices['__error__']}\n"
            "请确认依赖安装成功（openvino>=2026.0）。"
        )

    real = {k: v for k, v in devices.items() if not k.startswith("__")}
    if not real:
        if allow_non_intel:
            return True, "警告：未枚举到推理设备，已按 --allow-non-intel 继续。"
        return False, "未枚举到任何 OpenVINO 推理设备。"

    has_npu = any(d.startswith("NPU") for d in real)
    has_gpu = any(d.startswith("GPU") for d in real)
    cpu_name = next((v for k, v in real.items() if k.startswith("CPU")), "")

    if has_npu or has_gpu:
        return True, ""

    if "intel" in cpu_name.lower():
        # 仅 CPU 可用：能完成任务，只是慢。不阻断，但如实告知。
        return True, (
            "提示：未检测到 Intel iGPU / NPU，本次将在 CPU 上推理，耗时会明显增加。\n"
            "  在英特尔 AI PC（Core Ultra）上可获得 iGPU / NPU 加速。"
        )

    if allow_non_intel:
        return True, "警告：已跳过 Intel 平台门禁（--allow-non-intel），仅供协议自测。"

    return False, (
        "本 skill 需要英特尔 AI PC 平台（Intel Core / Core Ultra + OpenVINO 可用设备）。\n"
        f"  当前枚举到的设备：{', '.join(real.keys()) or '(无)'}\n"
        f"  CPU：{cpu_name or '(未知)'}"
    )


# ==========================================================================
# 运行时副本同步（热更新安全）
# server 从 %USERPROFILE%\.openvino\runtime\local-devlog\ 运行，
# 而不是直接从安装目录跑；脚本内容变化时自动重启 server。
# ==========================================================================
RUNTIME_FILES = [
    "server.py",
    "common.py",
    "backends.py",
    "devlog_engine.py",
    "evidence.py",
]


def _hash_files(src: Path) -> str:
    h = hashlib.sha256()
    for name in sorted(RUNTIME_FILES):
        f = src / name
        if f.is_file():
            h.update(name.encode("utf-8"))
            h.update(f.read_bytes())
    return h.hexdigest()


def sync_runtime() -> tuple[Path, bool]:
    """把运行时脚本同步到副本目录。返回 (副本目录, 内容是否发生变化)。"""
    src = Path(__file__).resolve().parent
    dst = common.runtime_dir()
    stamp = dst / ".sync.sha256"

    new_hash = _hash_files(src)
    old_hash = stamp.read_text(encoding="utf-8").strip() if stamp.is_file() else ""

    changed = new_hash != old_hash
    if changed:
        for name in RUNTIME_FILES:
            f = src / name
            if f.is_file():
                shutil.copy2(f, dst / name)
        stamp.write_text(new_hash, encoding="utf-8")
        LOG.log(f"runtime synced to {dst}, hash={new_hash[:12]}")
    return dst, changed


# ==========================================================================
# server 生命周期
# ==========================================================================
def spawn_server(runtime: Path) -> None:
    """在后台拉起 server.py。

    宿主若自带进程管理器（如 Marvis 的 server-dog），应改为通过它申请启动，
    以便宿主统一做内存预算与退出清理。此处为 host-agnostic 的自启实现。
    """
    server_py = runtime / "server.py"
    env = os.environ.copy()
    # server 从副本目录运行，拿不到安装目录的 info.json，用环境变量告知
    env["LOCAL_DEVLOG_ROOT"] = str(common.skill_root())

    kwargs: dict = {"cwd": str(runtime), "env": env,
                    "stdin": subprocess.DEVNULL,
                    "stdout": subprocess.DEVNULL,
                    "stderr": subprocess.DEVNULL}
    if os.name == "nt":
        DETACHED_PROCESS = 0x00000008
        CREATE_NEW_PROCESS_GROUP = 0x00000200
        CREATE_NO_WINDOW = 0x08000000
        kwargs["creationflags"] = (DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
                                   | CREATE_NO_WINDOW)
    else:
        kwargs["start_new_session"] = True

    LOG.log(f"spawning server: {server_py}")
    subprocess.Popen([sys.executable, str(server_py)], **kwargs)


def shutdown_server() -> None:
    try:
        common.send({"op": "shutdown"}, timeout=10)
        LOG.log("shutdown sent")
    except Exception as exc:
        LOG.log(f"shutdown failed (probably not running): {exc}")


def ensure_server(runtime: Path, restart: bool) -> None:
    """确保 server 在跑；restart=True 时先停掉旧进程（脚本已更新）。"""
    st = common.try_status(timeout=5)

    if st and restart:
        LOG.log("runtime changed, restarting server")
        shutdown_server()
        time.sleep(1.0)
        st = None

    if st:
        LOG.log(f"server already running, state={st.get('state')}")
        return

    spawn_server(runtime)

    deadline = time.time() + SPAWN_WAIT_TIMEOUT
    while time.time() < deadline:
        if common.try_status(timeout=3):
            LOG.log("server pipe is up")
            return
        time.sleep(1.0)
    raise ConnectionError("server did not come up within timeout")


def wait_ready(payload_for_pending: dict | None) -> dict:
    """轮询到 running 为止。

    downloading / loading 期间持续等待；超过 DOWNLOAD_WAIT_TIMEOUT 则保存
    挂起请求并以退出码 3 结束，提示用户执行 --continue。
    """
    deadline = time.time() + DOWNLOAD_WAIT_TIMEOUT
    retries = 0
    last_state = ""

    while time.time() < deadline:
        st = common.try_status(timeout=10)
        if st is None:
            time.sleep(READY_POLL_INTERVAL)
            continue

        state = st.get("state", "")
        if state != last_state:
            LOG.log(f"server state -> {state}")
            _print_state_hint(state, st)
            last_state = state

        if state == STATE_RUNNING:
            return st

        if state == STATE_ERROR:
            retries += 1
            LOG.log(f"server error (retry {retries}/{ERROR_RETRY_MAX}): "
                    f"{st.get('error', '')[:400]}")
            if retries > ERROR_RETRY_MAX:
                print("服务初始化反复失败，请查看日志：")
                print(f"  {LOG.path}")
                sys.exit(EXIT_ERROR)
            shutdown_server()
            time.sleep(2.0)
            runtime, _ = sync_runtime()
            spawn_server(runtime)
            time.sleep(2.0)
            continue

        time.sleep(READY_POLL_INTERVAL)

    # 超时：保存挂起请求
    if payload_for_pending is not None:
        try:
            with open(common.pending_file(), "w", encoding="utf-8") as fh:
                json.dump(payload_for_pending, fh, ensure_ascii=False, indent=1)
            LOG.log(f"pending request saved to {common.pending_file()}")
        except Exception as exc:
            LOG.log(f"failed to save pending request: {exc}")

    print("模型正在下载, 请用命令 'scripts\\run.ps1 --continue' 继续运行")
    sys.exit(EXIT_DOWNLOADING)


def _print_state_hint(state: str, st: dict) -> None:
    if state == STATE_DOWNLOADING:
        pct = st.get("progress")
        if isinstance(pct, (int, float)) and pct > 0:
            print(f"正在下载模型... {pct:.0f}%")
        else:
            print("正在下载模型（首次约 0.9 GiB）...")
    elif state == STATE_LOADING:
        print(f"正在加载模型到 {st.get('device') or '推理设备'}...")


# ==========================================================================
# 子命令
# ==========================================================================
def cmd_doctor(devices: dict) -> int:
    print("=== 设备自检 ===")
    if "__error__" in devices:
        print(f"OpenVINO 不可用: {devices['__error__']}")
    else:
        ver = devices.get("__version__")
        if ver:
            print(f"OpenVINO 版本: {ver}")
        for k, v in devices.items():
            if not k.startswith("__"):
                print(f"  {k:8s} {v}")

    print("\n=== 推理后端自检 ===")
    try:
        import backends
        for name, ok, detail in backends.probe_all():
            mark = "可用" if ok else "不可用"
            print(f"  {name:16s} {mark:6s} {detail}")
    except Exception as exc:
        print(f"  后端探测失败: {exc}")

    print("\n=== 服务状态 ===")
    st = common.try_status(timeout=5)
    if st is None:
        print("  server 未运行（首次请求时会自动拉起）")
    else:
        print(f"  state={st.get('state')} pid={st.get('pid')} "
              f"uptime={st.get('uptime_s', 0):.0f}s "
              f"backend={st.get('backend')} device={st.get('device')}")
        if st.get("error"):
            print(f"  最近错误: {str(st['error'])[:300]}")

    print(f"\n日志目录: {common.log_dir()}")
    print("本 skill 全程在 localhost 完成推理，不访问任何云服务。")
    return EXIT_OK


def load_pending() -> dict | None:
    p = common.pending_file()
    if not p.is_file():
        return None
    try:
        with open(p, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except Exception as exc:
        LOG.log(f"failed to read pending: {exc}")
        return None


def clear_pending() -> None:
    try:
        common.pending_file().unlink(missing_ok=True)
    except Exception:
        pass


# ==========================================================================
# 主流程
# ==========================================================================
def parse_rejected(items: list[str]) -> list[dict]:
    """把 "方案|理由" 解析成结构化列表。缺少理由时理由留空，由引擎标待补充。"""
    out = []
    for raw in items:
        if "|" in raw:
            option, reason = raw.split("|", 1)
        else:
            option, reason = raw, ""
        option = option.strip()
        reason = reason.strip()
        if option:
            out.append({"option": option, "reason": reason})
    return out


def main(argv: list[str]) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    LOG.log(f"start argv={argv}")

    devices = detect_devices()

    if args.doctor:
        return cmd_doctor(devices)

    ok, note = hardware_gate(devices, args.allow_non_intel)
    if not ok:
        print(note)
        LOG.log("hardware gate rejected")
        return EXIT_ERROR
    if note:
        print(note)

    # --continue：取回挂起请求
    if args.do_continue:
        pending = load_pending()
        if pending is None:
            print("没有待续传的请求。")
            return EXIT_OK
        LOG.log("resuming pending request")
        intent = pending.get("intent")
        request = pending
    else:
        if not args.intent:
            print("请提供一句话意图，例如：")
            print('  scripts\\run.ps1 "改用 opaque handle 表示 Backend 资源"')
            return EXIT_ERROR
        intent = args.intent
        request = None

    # 运行时副本 + server
    try:
        runtime, changed = sync_runtime()
        ensure_server(runtime, restart=changed)
    except Exception as exc:
        print(f"无法启动本地推理服务：{exc}")
        print(f"  日志：{LOG.path}")
        LOG.log(f"ensure_server failed: {exc}")
        return EXIT_CONN

    # 确认模型档位。放在 wait_ready 之前，让切档的下载/加载也能被统一等待。
    if args.do_continue:
        # 挂起请求里若缺字段（旧版本写入的），回落默认档位而不是崩掉
        tier = ((request or {}).get("model_tier") or "1.5b").lower()
    else:
        tier = (args.model or "1.5b").lower()
    if tier not in ("1.5b", "7b"):
        print(f"未知的模型档位：{tier}（可选 1.5b / 7b）")
        return EXIT_ERROR
    try:
        ens = common.send({"op": "ensure_model", "tier": tier}, timeout=30)
        if not ens.get("ok"):
            print(f"模型档位设置失败：{ens.get('error')}")
            return EXIT_ERROR
        if ens.get("switching"):
            LOG.log(f"server is switching to tier {tier}")
    except Exception as exc:
        print(f"与本地推理服务通信失败：{exc}")
        LOG.log(f"ensure_model failed: {exc}")
        return EXIT_CONN

    # 采集证据（必须在 client 侧，cwd 才是用户仓库）
    if request is None:
        import evidence
        try:
            pack = evidence.collect(
                cwd=Path.cwd(),
                commits=args.commits,
                test_log=Path(args.test_log) if args.test_log else None,
            )
        except evidence.NotARepository as exc:
            print(f"当前目录不是 git 仓库：{exc}")
            return EXIT_ERROR
        except Exception as exc:
            print(f"证据采集失败：{exc}")
            LOG.log(f"evidence.collect failed: {exc}")
            return EXIT_ERROR

        if pack.get("empty"):
            print("未检测到任何代码变更，没有可记录的决策。")
            print("  提示：用 --commits N 分析已提交的历史。")
            return EXIT_OK

        request = {
            "op": "request",
            "args": argv,
            "intent": intent,
            "evidence": pack,
            "rejected": parse_rejected(args.rejected),
            "model_tier": tier,
            "out": args.out,
            "dry_run": bool(args.dry_run),
        }

    # 等待就绪（超时则保存挂起请求）
    wait_ready(payload_for_pending=request)

    # 送 server 做字段抽取
    t0 = time.time()
    try:
        resp = common.send(request, timeout=600)
    except Exception as exc:
        print(f"与本地推理服务通信失败：{exc}")
        LOG.log(f"request failed: {exc}")
        return EXIT_CONN

    if not resp.get("ok"):
        print(f"错误: {resp.get('error')}")
        LOG.log(f"server returned error: {resp.get('error')}")
        return EXIT_ERROR

    elapsed = time.time() - t0
    clear_pending()

    # 渲染并落盘（client 侧，cwd 相关）
    import devlog_engine

    fields = resp.get("fields", {})
    out_path = Path(request.get("out") or "DEVLOG.md")
    dry_run = bool(request.get("dry_run"))

    adr_no = devlog_engine.next_adr_number(out_path)
    entry = devlog_engine.render_adr(
        fields=fields,
        adr_no=adr_no,
        intent=request.get("intent", ""),
        evidence=request.get("evidence", {}),
        meta={
            "backend": resp.get("backend", "?"),
            "device": resp.get("device", "?"),
            "model": resp.get("model", "?"),
        },
    )

    unverified_n, unverified_fields = devlog_engine.count_unverified(fields)

    if dry_run:
        print(entry)
        print("--- 以上为 --dry-run 预览，未写入文件 ---")
    else:
        try:
            devlog_engine.append_entry(out_path, entry)
        except Exception as exc:
            print(f"写入失败：{exc}")
            LOG.log(f"append_entry failed: {exc}")
            return EXIT_ERROR
        print(f"已追加: {out_path}  条目: ADR-{adr_no:04d}")

    print(f"后端: {resp.get('backend', '?')}  设备: {resp.get('device', '?')}  "
          f"模型: {resp.get('model', '?')}")
    detail = f" ({', '.join(unverified_fields)})" if unverified_fields else ""
    print(f"耗时: {elapsed:.1f}s   未验证字段: {unverified_n}{detail}")

    LOG.log(f"done in {elapsed:.1f}s, unverified={unverified_n}")
    return EXIT_OK


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except KeyboardInterrupt:
        print("\n已中断。")
        sys.exit(EXIT_ERROR)
