"""backends.py — 三级本地推理后端。

优先级（全部在 localhost，绝无云端路径）：

  1. isvik        —— 本机 Isvik 运行时（Nim + OpenVINO C API），HTTP/7317
                     自研内核，NPU→iGPU→CPU 自动调度 + 编译缓存
  2. openvino-genai —— 纯 Python 路径，pip 装完即可用
                     保证任何人都能复现，不需要编译 Isvik
  3. rule         —— 无模型降级：不产出任何推断内容，
                     只输出确定的事实与证据锚点，其余标「待补充」

第 3 级不是"凑数的兜底"，而是本 skill「宁缺毋造」原则的体现：
没有模型时诚实留空，而不是编造一段读起来通顺的假日志。
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from pathlib import Path

# 环境变量开关
ENV_FORCE_BACKEND = "LOCAL_DEVLOG_BACKEND"   # isvik | genai | rule
ENV_FORCE_DEVICE = "LOCAL_DEVLOG_DEVICE"     # CPU | GPU | GPU.0 | NPU
ENV_ISVIK_BASE = "ISVIK_BASE_URL"
ENV_ISVIK_PORT = "ISVIK_PORT"
ENV_ISVIK_KEY = "ISVIK_API_KEY"

ISVIK_DEFAULT_PORT = 7317
HTTP_TIMEOUT_PROBE = 3.0
HTTP_TIMEOUT_GEN = 600.0

# Qwen2.5 系列的 ChatML 标记
IM_START = "<|im_start|>"
IM_END = "<|im_end|>"


# ==========================================================================
# 基类
# ==========================================================================
class Backend:
    name = "base"
    device = ""
    is_llm = True

    def generate(self, system: str, user: str,
                 max_tokens: int = 512, temperature: float = 0.2) -> str:
        raise NotImplementedError

    def close(self) -> None:
        pass


# ==========================================================================
# 1) Isvik 后端
# ==========================================================================
def _isvik_base() -> str:
    base = os.environ.get(ENV_ISVIK_BASE)
    if base:
        return base.rstrip("/")
    port = os.environ.get(ENV_ISVIK_PORT) or str(ISVIK_DEFAULT_PORT)
    return f"http://127.0.0.1:{port}"


def _http_json(url: str, payload: dict | None = None,
               timeout: float = HTTP_TIMEOUT_PROBE) -> dict:
    """发一个 JSON 请求。payload 为 None 时是 GET。"""
    data = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"

    key = os.environ.get(ENV_ISVIK_KEY)
    if key:
        # Isvik 同时接受 Authorization: Bearer 与 x-api-key
        headers["Authorization"] = f"Bearer {key}"
        headers["x-api-key"] = key

    req = urllib.request.Request(url, data=data, headers=headers,
                                 method="POST" if data else "GET")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode("utf-8", errors="replace")
    return json.loads(raw) if raw.strip() else {}


def _dig(obj, *names, default=""):
    """在嵌套 dict 中按多个候选字段名查找第一个命中的字符串值。

    Isvik 的私有端点（/api/runtime 等）字段命名以其实现为准，此处做
    宽松匹配。即使全部未命中也不影响推理：generate 走的是标准
    OpenAI /v1/chat/completions 协议，只是设备名显示为未知。
    """
    if not isinstance(obj, dict):
        return default
    for n in names:
        if n in obj and isinstance(obj[n], (str, int, float)):
            return str(obj[n])
    for v in obj.values():
        if isinstance(v, dict):
            got = _dig(v, *names, default="")
            if got:
                return got
    return default


class IsvikBackend(Backend):
    name = "isvik"

    def __init__(self, model_id: str, log=None) -> None:
        self.base = _isvik_base()
        self.log = log
        self.model = self._resolve_model(model_id)
        self.device = self._resolve_device()

    # ---- 探测 ----
    @staticmethod
    def probe() -> tuple[bool, str]:
        base = _isvik_base()
        try:
            _http_json(f"{base}/api/health")
            return True, f"{base} 健康检查通过"
        except urllib.error.URLError as exc:
            return False, f"{base} 不可达（{getattr(exc, 'reason', exc)}）"
        except Exception as exc:
            return False, f"{base} 探测失败（{exc}）"

    # ---- 模型 ----
    def _resolve_model(self, model_id: str) -> str:
        """在 Isvik 已导入的模型中找到匹配项；必要时请求加载。"""
        want = model_id.split("/")[-1].lower()

        listed: list[str] = []
        try:
            data = _http_json(f"{self.base}/api/models")
            listed = self._extract_model_ids(data)
        except Exception as exc:
            self._log(f"list models failed: {exc}")

        # 精确匹配优先，其次按关键词模糊匹配
        chosen = ""
        for m in listed:
            if m.lower() == want:
                chosen = m
                break
        if not chosen:
            for m in listed:
                low = m.lower()
                if "coder" in low and ("1.5b" in low or "7b" in low):
                    chosen = m
                    break
        if not chosen and listed:
            chosen = listed[0]
        if not chosen:
            # Isvik 里没有可用模型时，仍把期望的 id 传给它，由其自行报错，
            # 报错内容会通过 generate 的异常上抛，便于用户定位。
            chosen = want

        # 若当前未加载该模型，尝试请求加载（字段名做多种尝试）
        try:
            runtime = _http_json(f"{self.base}/api/runtime")
            active = _dig(runtime, "model", "Model", "model_id", "active_model")
        except Exception:
            active = ""

        if active.lower() != chosen.lower():
            for body in ({"model": chosen}, {"model_id": chosen}, {"id": chosen}):
                try:
                    _http_json(f"{self.base}/api/load", payload=body, timeout=180.0)
                    self._log(f"requested isvik to load {chosen} via {list(body)[0]}")
                    break
                except Exception as exc:
                    self._log(f"load with {list(body)[0]} failed: {exc}")

        return chosen

    @staticmethod
    def _extract_model_ids(data) -> list[str]:
        """从 /api/models 的响应里尽力提取模型 id 列表。"""
        out: list[str] = []

        def walk(node):
            if isinstance(node, str):
                return
            if isinstance(node, list):
                for it in node:
                    if isinstance(it, str):
                        out.append(it)
                    elif isinstance(it, dict):
                        got = _dig(it, "id", "Id", "model_id", "name", "Name")
                        if got:
                            out.append(got)
                    else:
                        walk(it)
                return
            if isinstance(node, dict):
                for v in node.values():
                    walk(v)

        walk(data)
        # 去重保序
        seen = set()
        uniq = []
        for m in out:
            if m and m not in seen:
                seen.add(m)
                uniq.append(m)
        return uniq

    def _resolve_device(self) -> str:
        try:
            runtime = _http_json(f"{self.base}/api/runtime")
            dev = _dig(runtime, "device", "Device", "physical_device",
                       "execution_device", "actual_device")
            return dev or "unknown"
        except Exception as exc:
            self._log(f"resolve device failed: {exc}")
            return "unknown"

    def _log(self, msg: str) -> None:
        if self.log is not None:
            self.log.log(f"[isvik] {msg}")

    # ---- 推理：标准 OpenAI Chat Completions ----
    def generate(self, system: str, user: str,
                 max_tokens: int = 512, temperature: float = 0.2) -> str:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": False,
        }
        data = _http_json(f"{self.base}/v1/chat/completions",
                          payload=payload, timeout=HTTP_TIMEOUT_GEN)
        try:
            return data["choices"][0]["message"]["content"] or ""
        except Exception:
            # 少数实现把内容放在 text 字段
            got = _dig(data, "content", "text")
            if got:
                return got
            raise RuntimeError(f"unexpected response shape: {str(data)[:300]}")


# ==========================================================================
# 2) openvino-genai 后端
# ==========================================================================
def _device_order() -> list[str]:
    """设备优先级：显式指定 > Intel iGPU > CPU。

    NPU 有意不进默认顺序：NPU 上跑 LLM 需要静态形状的专门导出，
    通用 *-int4-ov IR 直接指到 NPU 大概率编译失败。
    需要实测 NPU 时用 LOCAL_DEVLOG_DEVICE=NPU 显式指定。
    """
    forced = os.environ.get(ENV_FORCE_DEVICE)
    if forced:
        return [forced]

    order: list[str] = []
    try:
        import openvino as ov
        available = ov.Core().available_devices
    except Exception:
        return ["CPU"]

    for d in available:
        if d.startswith("GPU"):
            order.append(d)
    if any(d == "CPU" for d in available):
        order.append("CPU")
    return order or ["CPU"]


class GenAIBackend(Backend):
    name = "openvino-genai"

    def __init__(self, model_dir: Path, log=None) -> None:
        import openvino_genai as ov_genai

        self.log = log
        self._genai = ov_genai
        self.pipe = None
        self.device = ""

        errors = []
        for dev in _device_order():
            try:
                self._log(f"trying LLMPipeline on {dev}")
                self.pipe = ov_genai.LLMPipeline(str(model_dir), dev)
                self.device = dev
                self._log(f"pipeline ready on {dev}")
                break
            except Exception as exc:
                errors.append(f"{dev}: {exc}")
                self._log(f"device {dev} failed: {exc}")

        if self.pipe is None:
            raise RuntimeError("no usable device for LLMPipeline; " + " | ".join(errors))

    @staticmethod
    def probe() -> tuple[bool, str]:
        try:
            import openvino_genai  # noqa: F401
        except Exception as exc:
            return False, f"openvino-genai 未安装（{exc}）"
        return True, f"可用，候选设备 {', '.join(_device_order())}"

    def _log(self, msg: str) -> None:
        if self.log is not None:
            self.log.log(f"[genai] {msg}")

    def _build_prompt(self, system: str, user: str) -> str:
        """优先用模型自带 chat template，失败则手工拼 ChatML。"""
        messages = [{"role": "system", "content": system},
                    {"role": "user", "content": user}]
        try:
            tok = self.pipe.get_tokenizer()
            return tok.apply_chat_template(messages, add_generation_prompt=True)
        except Exception:
            return (f"{IM_START}system\n{system}{IM_END}\n"
                    f"{IM_START}user\n{user}{IM_END}\n"
                    f"{IM_START}assistant\n")

    def generate(self, system: str, user: str,
                 max_tokens: int = 512, temperature: float = 0.2) -> str:
        cfg = self._genai.GenerationConfig()
        cfg.max_new_tokens = max_tokens
        if temperature and temperature > 0:
            cfg.temperature = temperature
            cfg.do_sample = True
        else:
            cfg.do_sample = False

        prompt = self._build_prompt(system, user)
        result = self.pipe.generate(prompt, cfg)
        text = str(result)

        # 部分版本会带回 ChatML 结束标记，做一次裁剪
        for marker in (IM_END, "<|endoftext|>"):
            idx = text.find(marker)
            if idx >= 0:
                text = text[:idx]
        return text.strip()

    def close(self) -> None:
        self.pipe = None


# ==========================================================================
# 3) 规则降级后端
# ==========================================================================
class RuleBackend(Backend):
    """无 LLM 可用时的降级路径。

    刻意不实现 generate：调用方（devlog_engine）通过 is_llm 判断后走
    纯规则渲染，只输出能从证据中直接确定的内容，其余标「待补充」。
    """
    name = "rule-template"
    is_llm = False

    def __init__(self, reason: str = "") -> None:
        self.device = "n/a"
        self.reason = reason

    @staticmethod
    def probe() -> tuple[bool, str]:
        return True, "始终可用（无模型时的诚实降级路径）"

    def generate(self, system: str, user: str,
                 max_tokens: int = 512, temperature: float = 0.2) -> str:
        raise RuntimeError("rule backend does not generate text")


# ==========================================================================
# 工厂与探测
# ==========================================================================
def probe_all() -> list[tuple[str, bool, str]]:
    """供 --doctor 使用：逐个探测后端可用性。"""
    results = []
    for cls in (IsvikBackend, GenAIBackend, RuleBackend):
        try:
            ok, detail = cls.probe()
        except Exception as exc:
            ok, detail = False, f"探测异常：{exc}"
        results.append((cls.name, ok, detail))
    return results


def create_backend(model_dir: Path, model_id: str, log=None) -> Backend:
    """按优先级创建后端。全部失败时返回规则降级后端（不抛异常）。"""
    forced = (os.environ.get(ENV_FORCE_BACKEND) or "").strip().lower()

    def _try_isvik():
        ok, detail = IsvikBackend.probe()
        if not ok:
            raise RuntimeError(detail)
        return IsvikBackend(model_id=model_id, log=log)

    def _try_genai():
        ok, detail = GenAIBackend.probe()
        if not ok:
            raise RuntimeError(detail)
        return GenAIBackend(model_dir=model_dir, log=log)

    if forced == "isvik":
        return _try_isvik()
    if forced == "genai":
        return _try_genai()
    if forced == "rule":
        return RuleBackend(reason=f"由 {ENV_FORCE_BACKEND}=rule 强制指定")

    reasons = []
    for label, fn in (("isvik", _try_isvik), ("genai", _try_genai)):
        try:
            backend = fn()
            if log is not None:
                log.log(f"backend selected: {backend.name} on {backend.device}")
            return backend
        except Exception as exc:
            reasons.append(f"{label}: {exc}")
            if log is not None:
                log.log(f"backend {label} unavailable: {exc}")

    if log is not None:
        log.log("falling back to rule backend: " + " | ".join(reasons))
    return RuleBackend(reason=" | ".join(reasons))
