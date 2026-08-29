"""devlog_engine.py — ADR 抽取与渲染。

字段职责划分是本 skill 的核心，务必先读这段：

  由「规则」产生（绝不经过语言模型）：
    - Status                  当前日期 + 固定状态
    - Alternatives Considered  只来自用户 --rejected 输入
    - Verified Facts           只来自测试日志的正则匹配结果
    - Evidence                 只来自 git / 日志的真实锚点

  由「语言模型」产生（且必须以 diff 为依据）：
    - Context / Decision / Non-Goals / Pitfalls

为什么 Alternatives Considered 不能交给模型？
被否决的方案不会在代码里留下任何痕迹 —— 它在信息论上就不可能从 diff 反推。
让模型去写这一节，等于让它编造。因此没有 --rejected 输入时，此节
诚实输出「待补充」，并在结尾提示用户如何补。

为什么 Verified Facts 不能交给模型？
耗时、测试计数、版本号这类数字一旦被编造，整份记录就失去了审计价值。
模型负责组织语言，数字只能来自真实输出的正则匹配。
"""
from __future__ import annotations

import re
from datetime import date
from pathlib import Path

UNVERIFIED = "未验证"
TODO_MARK = "待补充"

# 需要模型产出的字段及其提问预算
LLM_FIELDS = ("context", "decision", "non_goals", "pitfalls")

MAX_TOKENS_SHORT = 220
MAX_TOKENS_MEDIUM = 320
TEMPERATURE = 0.15   # 记录类任务要稳定复现，温度压低

SYSTEM_PROMPT = (
    "你是工程决策记录助手，负责把代码变更整理成简洁的中文技术记录。\n"
    "严格规则：\n"
    "1. 只依据提供的证据作答，不得推断、不得补充证据里没有的信息。\n"
    "2. 不得编造任何数字（耗时、版本号、测试数量、性能指标）。\n"
    "3. 证据不足以回答时，只输出四个字：待补充\n"
    "4. 直接输出内容本身，不要加标题、不要加解释、不要用 markdown 代码块。\n"
    "5. 用简体中文，语气克制，不使用营销辞令。"
)

# 幻觉守卫：这些形态的数字如果没在证据中出现过，就是模型编的
_SUSPECT_NUMBER_PATTERNS = [
    re.compile(r'\b\d+(?:\.\d+)?\s*(?:ms|毫秒)\b', re.IGNORECASE),
    re.compile(r'\b\d+(?:\.\d+)?\s*(?:s|秒|sec|seconds)\b', re.IGNORECASE),
    re.compile(r'\b\d+(?:\.\d+)?\s*(?:tok/s|tokens?/s|it/s|ops/s|fps)\b', re.IGNORECASE),
    re.compile(r'\bv?\d+\.\d+\.\d+(?:[-+][\w.]+)?\b'),
    re.compile(r'\b\d+(?:\.\d+)?\s*(?:%|percent)\b', re.IGNORECASE),
    re.compile(r'\b\d+(?:\.\d+)?\s*(?:GiB|MiB|KiB|GB|MB|KB)\b', re.IGNORECASE),
]


# ==========================================================================
# 证据 → 文本视图
# ==========================================================================
def _evidence_digest(evidence: dict) -> str:
    """把证据包压缩成送模型的紧凑文本。"""
    repo = evidence.get("repo", {})
    stats = evidence.get("stats", {})
    lines = [
        f"仓库分支：{repo.get('branch', '?')}",
        f"变更范围：{'最近提交' if evidence.get('mode') == 'commits' else '工作区未提交变更'}",
        f"变更统计：{stats.get('files', 0)} 个文件，+{stats.get('added', 0)} / -{stats.get('deleted', 0)} 行",
    ]

    commits = evidence.get("commits") or []
    if commits:
        lines.append("提交记录：")
        for c in commits[:8]:
            lines.append(f"  [{c.get('short')}] {c.get('subject')}")

    files = evidence.get("files") or []
    if files:
        lines.append("变更文件：")
        for f in files[:15]:
            lines.append(f"  {f.get('status_cn')} {f.get('path')} "
                         f"(+{f.get('added')}/-{f.get('deleted')})")

    untracked = evidence.get("untracked") or []
    if untracked:
        lines.append(f"未跟踪的新文件：{', '.join(untracked[:8])}")

    diff = evidence.get("diff_text") or ""
    if diff:
        lines.append("代码差异（可能已按预算截断）：")
        lines.append(diff)

    return "\n".join(lines)


def _evidence_corpus(evidence: dict) -> str:
    """用于幻觉检测的证据全文：模型输出的数字必须能在这里找到。"""
    parts = [evidence.get("diff_text") or ""]
    for c in evidence.get("commits") or []:
        parts.append(c.get("subject") or "")
        parts.append(c.get("body") or "")
    for f in evidence.get("files") or []:
        parts.append(f"{f.get('path')} {f.get('added')} {f.get('deleted')}")
    stats = evidence.get("stats", {})
    parts.append(f"{stats.get('files')} {stats.get('added')} {stats.get('deleted')}")
    tl = evidence.get("test_log")
    if tl:
        parts.append(tl.get("excerpt") or "")
    return "\n".join(parts)


# ==========================================================================
# 输出清洗与幻觉守卫
# ==========================================================================
def _clean(text: str) -> str:
    """去掉模型常见的多余包装。"""
    t = (text or "").strip()
    # 去 markdown 代码块围栏
    t = re.sub(r'^```[\w-]*\n?', '', t)
    t = re.sub(r'\n?```$', '', t)
    # 去 ChatML 残留
    for mark in ("<|im_end|>", "<|im_start|>", "<|endoftext|>"):
        t = t.replace(mark, "")
    # 去模型爱加的前缀
    t = re.sub(r'^(?:回答|答案|内容|输出)\s*[:：]\s*', '', t)
    # 去掉被当成标题输出的行
    t = re.sub(r'^#{1,6}\s+.*\n', '', t)
    return t.strip()


def _is_todo(text: str) -> bool:
    t = (text or "").strip().strip("。.，,")
    return (not t) or (t in (TODO_MARK, UNVERIFIED)) or len(t) < 4


def _guard_numbers(text: str, corpus: str, log=None) -> tuple[str, list[str]]:
    """剔除证据中不存在的性能类数字。

    这是「不伪造」原则的自动执行环节：模型可以组织语言，但一旦它写出
    证据里没有的耗时 / 版本号 / 吞吐量，就地替换为「未验证」。
    """
    removed: list[str] = []
    out = text
    for pat in _SUSPECT_NUMBER_PATTERNS:
        for m in list(pat.finditer(out)):
            token = m.group(0)
            # 归一化比较：去空格、统一小写
            needle = re.sub(r'\s+', '', token).lower()
            hay = re.sub(r'\s+', '', corpus).lower()
            if needle not in hay:
                removed.append(token)
                out = out.replace(token, f"（{UNVERIFIED}）")
    if removed and log is not None:
        log.log(f"[guard] removed unsupported numbers: {removed}")
    return out, removed


def _ask(backend, question: str, digest: str, corpus: str,
         max_tokens: int, log=None) -> tuple[str, list[str]]:
    """就单个字段提问。

    每字段一次独立的小请求，而不是让模型一次生成整篇。
    原因：1.5B 级模型在长输出上的结构保持能力很差，拆成受约束的短问答后
    质量显著稳定，且失败可以被隔离到单个字段。
    """
    user = f"{question}\n\n=== 证据开始 ===\n{digest}\n=== 证据结束 ==="
    try:
        raw = backend.generate(SYSTEM_PROMPT, user,
                               max_tokens=max_tokens, temperature=TEMPERATURE)
    except Exception as exc:
        if log is not None:
            log.log(f"[ask] generate failed: {exc}")
        return TODO_MARK, []

    text = _clean(raw)
    if _is_todo(text):
        return TODO_MARK, []
    text, removed = _guard_numbers(text, corpus, log=log)
    return text, removed


# ==========================================================================
# 规则字段
# ==========================================================================
def _facts_from_test_log(evidence: dict) -> list[dict]:
    """只从测试日志的正则命中里产出实测事实。没有日志就没有事实。"""
    tl = evidence.get("test_log")
    if not tl or not tl.get("metrics"):
        return []

    label_cn = {
        "duration": "耗时", "tests_passed": "测试通过", "tests_failed": "测试失败",
        "tests_total": "测试总数", "throughput": "吞吐", "percentile": "分位延迟",
        "version": "版本", "device": "设备",
    }

    facts = []
    for key, hits in tl["metrics"].items():
        for h in hits[:3]:
            facts.append({
                "metric": label_cn.get(key, key),
                "value": h.get("value", ""),
                "anchor": h.get("anchor", ""),
            })
    return facts


def _alternatives_from_input(rejected: list[dict]) -> list[dict]:
    """被否方案只能来自用户显式输入，不接受任何推断来源。"""
    out = []
    for item in rejected or []:
        option = (item.get("option") or "").strip()
        reason = (item.get("reason") or "").strip()
        if option:
            out.append({"option": option, "reason": reason or TODO_MARK})
    return out


def _anchor_lines(evidence: dict) -> list[str]:
    lines = []
    seen = set()
    for a in evidence.get("anchors") or []:
        ref = a.get("ref", "")
        if not ref or ref in seen:
            continue
        seen.add(ref)
        kind = a.get("kind", "")
        detail = a.get("detail", "")
        prefix = {"commit": "commit", "file": "", "test": "log"}.get(kind, kind)
        label = f"`{prefix} {ref}`".replace("` ", "`") if prefix else f"`{ref}`"
        lines.append(f"{label} — {detail}" if detail else label)
    return lines


# ==========================================================================
# 抽取（server 侧调用）
# ==========================================================================
def extract_fields(evidence: dict, intent: str, rejected: list[dict],
                   backend, log=None) -> dict:
    digest = _evidence_digest(evidence)
    corpus = _evidence_corpus(evidence)

    fields: dict = {
        "title": (intent or "").strip() or TODO_MARK,
        "status": f"已接受（{date.today().isoformat()}）",
        # 以下三项一律由规则产生
        "verified_facts": _facts_from_test_log(evidence),
        "alternatives": _alternatives_from_input(rejected),
        "anchors": _anchor_lines(evidence),
        "guard_removed": [],
        "degraded": False,
    }

    if not getattr(backend, "is_llm", True):
        # 规则降级：不产出任何推断内容，四个模型字段全部诚实留空
        for f in LLM_FIELDS:
            fields[f] = TODO_MARK
        fields["degraded"] = True
        if log is not None:
            log.log("[extract] rule-degraded mode, LLM fields left as TODO")
        return fields

    questions = {
        "context": (
            "用 2-3 句话说明这次变更的背景：改动前存在什么问题或什么需求，"
            "使得这次决策成为必要。不要描述改动本身。"),
        "decision": (
            "用 2-4 句话说明这次实际采用的技术决策是什么，以及它如何解决背景中的问题。"
            "要具体到模块、结构或做法。"),
        "non_goals": (
            "这次变更明确不打算解决什么？列出 1-3 条边界。"
            "只有当证据中能明确看出边界时才回答，否则输出：待补充"),
        "pitfalls": (
            "证据中是否存在修复某个具体问题的痕迹（例如修正边界条件、"
            "处理异常路径、纠正错误逻辑）？若有，按「现象 → 根因 → 修复」"
            "各一句话描述；若没有明确痕迹，输出：待补充"),
    }

    budgets = {
        "context": MAX_TOKENS_SHORT,
        "decision": MAX_TOKENS_MEDIUM,
        "non_goals": MAX_TOKENS_SHORT,
        "pitfalls": MAX_TOKENS_MEDIUM,
    }

    all_removed: list[str] = []
    for name in LLM_FIELDS:
        text, removed = _ask(backend, questions[name], digest, corpus,
                             budgets[name], log=log)
        fields[name] = text
        all_removed.extend(removed)
        if log is not None:
            log.log(f"[extract] {name}: {len(text)} chars"
                    + (f", guarded {len(removed)}" if removed else ""))

    fields["guard_removed"] = all_removed
    return fields


# ==========================================================================
# 渲染与落盘（client 侧调用）
# ==========================================================================
ADR_HEADING_RE = re.compile(r'^##\s+ADR-(\d{1,6})\b', re.MULTILINE)

FILE_HEADER = """# 工程决策日志（DEVLOG）

本文件由 local-devlog skill 在本地生成并追加，模型推理全程在本机完成。

记录约定：
- 每条为一个 ADR（Architecture Decision Record），编号递增，只追加不改写。
- `Alternatives Considered` 只登记作者显式提供的被否方案 —— 它无法从代码反推。
- `Verified Facts` 的数字全部来自真实测试输出的匹配结果，未提供输出时标「未验证」。
- 标为「待补充」的字段代表证据不足，**不是生成失败**，请作者手工补齐。

"""


def next_adr_number(out_path: Path) -> int:
    """扫描已有条目，返回下一个编号。文件不存在则从 1 开始。"""
    if not out_path.is_file():
        return 1
    try:
        text = out_path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return 1
    nums = [int(m.group(1)) for m in ADR_HEADING_RE.finditer(text)]
    return (max(nums) + 1) if nums else 1


def render_adr(fields: dict, adr_no: int, intent: str,
               evidence: dict, meta: dict) -> str:
    repo = evidence.get("repo", {})
    stats = evidence.get("stats", {})

    out: list[str] = []
    title = fields.get("title") or intent or TODO_MARK
    out.append(f"## ADR-{adr_no:04d} {title}")
    out.append("")
    out.append(f"- **Status**: {fields.get('status', TODO_MARK)}")
    out.append(f"- **Scope**: {repo.get('branch', '?')} @ "
               f"{repo.get('head_short', '?')} · "
               f"{stats.get('files', 0)} 文件 "
               f"+{stats.get('added', 0)}/-{stats.get('deleted', 0)}")
    out.append(f"- **Generated-By**: {meta.get('backend', '?')} / "
               f"{meta.get('device', '?')} / {meta.get('model', '?')}（本地推理）")
    if fields.get("degraded"):
        out.append("- **Mode**: 规则降级（无可用本地模型，仅保留确定事实）")
    out.append("")

    def section(name: str, body: str) -> None:
        out.append(f"### {name}")
        out.append("")
        out.append(body if body else TODO_MARK)
        out.append("")

    section("Context", fields.get("context", TODO_MARK))
    section("Decision", fields.get("decision", TODO_MARK))
    section("Non-Goals", fields.get("non_goals", TODO_MARK))

    # Alternatives Considered
    out.append("### Alternatives Considered")
    out.append("")
    alts = fields.get("alternatives") or []
    if alts:
        for a in alts:
            out.append(f"- **{a['option']}** —— 拒绝理由：{a['reason']}")
    else:
        out.append(f"{TODO_MARK}：本次未登记被否方案。")
        out.append("")
        out.append("> 被否决的方案不会在代码里留下痕迹，无法从 diff 反推，"
                   "因此本工具不会替你推测。")
        out.append("> 补充方式：`--rejected \"方案|拒绝理由\"`（可重复多次）。")
    out.append("")

    # Verified Facts
    out.append("### Verified Facts")
    out.append("")
    facts = fields.get("verified_facts") or []
    if facts:
        out.append("| 指标 | 值 | 证据锚点 |")
        out.append("| --- | --- | --- |")
        for f in facts:
            out.append(f"| {f['metric']} | `{f['value']}` | `{f['anchor']}` |")
    else:
        out.append(f"{UNVERIFIED}：本次未提供测试或 benchmark 输出。")
        out.append("")
        out.append("> 补充方式：`--test-log <路径>`，"
                   "工具只登记该文件中真实出现的数字。")
    out.append("")

    section("Pitfalls", fields.get("pitfalls", TODO_MARK))

    # Evidence
    out.append("### Evidence")
    out.append("")
    anchors = fields.get("anchors") or []
    if anchors:
        for line in anchors[:20]:
            out.append(f"- {line}")
    else:
        out.append(TODO_MARK)
    if evidence.get("diff_truncated"):
        out.append(f"- 说明：diff 总量 {evidence.get('diff_total_bytes', 0)} 字节，"
                   f"送入模型前已按预算截断；上列锚点覆盖完整变更位置。")
    out.append("")

    removed = fields.get("guard_removed") or []
    if removed:
        out.append(f"> 反幻觉守卫：本次拦截了 {len(removed)} 处证据中不存在的数字"
                   f"（{', '.join(removed[:5])}），已替换为「{UNVERIFIED}」。")
        out.append("")

    out.append("---")
    out.append("")
    return "\n".join(out)


def append_entry(out_path: Path, entry: str) -> None:
    """追加写入。文件不存在时先写入说明性头部。只追加，绝不改写已有内容。"""
    exists = out_path.is_file()
    if out_path.parent and not out_path.parent.exists():
        out_path.parent.mkdir(parents=True, exist_ok=True)

    with open(out_path, "a", encoding="utf-8", newline="\n") as fh:
        if not exists:
            fh.write(FILE_HEADER)
        fh.write(entry)
        if not entry.endswith("\n"):
            fh.write("\n")


def count_unverified(fields: dict) -> tuple[int, list[str]]:
    """统计因证据不足而留空的字段，供 client 在结尾如实报告。"""
    names = {
        "context": "Context", "decision": "Decision",
        "non_goals": "Non-Goals", "pitfalls": "Pitfalls",
    }
    missing = [label for key, label in names.items()
               if _is_todo(str(fields.get(key, "")))]

    if not (fields.get("alternatives") or []):
        missing.append("Alternatives Considered")
    if not (fields.get("verified_facts") or []):
        missing.append("Verified Facts")

    return len(missing), missing
