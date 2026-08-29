"""evidence.py — 本地证据采集。

从 git 仓库、测试/benchmark 输出中采集**可核对**的证据，产出结构化证据包。

两条硬规则：
  1. 所有"实测事实"（耗时、测试计数、版本号、设备名）一律用确定性正则
     从真实输出里抽取，绝不经过语言模型。模型只负责组织语言，不负责产生数字。
  2. 每条证据都带锚点（commit SHA / 文件:行号 / 日志行号），读者可逐条回查。

在 client 侧运行：只有 client 的 cwd 才是用户的仓库。
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

# 送进小模型的证据预算。
# 1.5B 模型在长上下文上的抽取质量会急剧下降，因此宁可截断也不整段灌入；
# 被截断的部分不会消失 —— 它们仍以锚点形式留在 Evidence 段落里可供回查。
MAX_TOTAL_DIFF_CHARS = 6000
MAX_FILE_DIFF_CHARS = 1500
MAX_FILES_DETAIL = 12
MAX_TEST_LOG_CHARS = 4000
GIT_TIMEOUT = 30


class NotARepository(Exception):
    """当前目录不在 git 仓库内。"""


# ==========================================================================
# git 封装
# ==========================================================================
def _git(cwd: Path, *args: str, check: bool = True) -> str:
    """执行 git 命令并返回 stdout。

    core.quotepath=false 让非 ASCII 路径原样输出，否则中文文件名会被转义成
    八进制序列，锚点就失去可读性。
    """
    cmd = ["git", "-c", "core.quotepath=false", *args]
    proc = subprocess.run(
        cmd, cwd=str(cwd), capture_output=True, timeout=GIT_TIMEOUT,
    )
    out = proc.stdout.decode("utf-8", errors="replace")
    if check and proc.returncode != 0:
        err = proc.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"git {' '.join(args)} failed: {err or proc.returncode}")
    return out


def _repo_info(cwd: Path) -> dict:
    try:
        root = _git(cwd, "rev-parse", "--show-toplevel").strip()
    except Exception as exc:
        raise NotARepository(str(cwd)) from exc
    if not root:
        raise NotARepository(str(cwd))

    branch = _git(cwd, "rev-parse", "--abbrev-ref", "HEAD", check=False).strip()
    head = _git(cwd, "rev-parse", "HEAD", check=False).strip()
    count = _git(cwd, "rev-list", "--count", "HEAD", check=False).strip()
    try:
        total = int(count)
    except ValueError:
        total = 0

    return {
        "root": root,
        "branch": branch or "(detached)",
        "head": head,
        "head_short": head[:8],
        "commit_count": total,
    }


# ==========================================================================
# 变更解析
# ==========================================================================
_STATUS_CN = {
    "A": "新增", "M": "修改", "D": "删除",
    "R": "重命名", "C": "复制", "T": "类型变更", "U": "未合并",
}


def _parse_numstat(text: str) -> dict[str, tuple[int, int]]:
    """解析 git diff --numstat：added deleted path。二进制文件用 - 表示。"""
    out: dict[str, tuple[int, int]] = {}
    for line in text.splitlines():
        parts = line.split("\t")
        if len(parts) < 3:
            continue
        a, d, path = parts[0], parts[1], parts[-1]
        added = int(a) if a.isdigit() else 0
        deleted = int(d) if d.isdigit() else 0
        out[path] = (added, deleted)
    return out


def _parse_name_status(text: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for line in text.splitlines():
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        code = parts[0][:1]
        path = parts[-1]
        out[path] = code
    return out


def _split_diff_by_file(diff_text: str) -> dict[str, str]:
    """把整段 diff 按文件切开，便于逐文件预算截断。"""
    chunks: dict[str, str] = {}
    current_path = ""
    buf: list[str] = []

    for line in diff_text.splitlines(keepends=True):
        if line.startswith("diff --git "):
            if current_path:
                chunks[current_path] = "".join(buf)
            buf = [line]
            # diff --git a/x b/x  → 取 b/ 之后的路径
            m = re.search(r' b/(.+)$', line.rstrip("\n"))
            current_path = m.group(1) if m else line.strip()
        else:
            buf.append(line)
    if current_path:
        chunks[current_path] = "".join(buf)
    return chunks


def _hunk_anchors(file_path: str, file_diff: str) -> list[dict]:
    """从 hunk header 提取行号锚点：@@ -a,b +c,d @@"""
    anchors = []
    for m in re.finditer(r'^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@', file_diff,
                         re.MULTILINE):
        start = int(m.group(1))
        length = int(m.group(2) or 1)
        end = start + max(0, length - 1)
        anchors.append({
            "kind": "file",
            "ref": f"{file_path}:{start}-{end}" if end > start else f"{file_path}:{start}",
            "detail": "变更区间",
        })
    return anchors


def _truncate_diff(chunks: dict[str, str]) -> tuple[str, bool]:
    """按预算拼接 diff，返回 (文本, 是否被截断)。"""
    pieces: list[str] = []
    total = 0
    truncated = False

    for i, (path, body) in enumerate(chunks.items()):
        if i >= MAX_FILES_DETAIL:
            truncated = True
            break
        piece = body
        if len(piece) > MAX_FILE_DIFF_CHARS:
            piece = piece[:MAX_FILE_DIFF_CHARS] + f"\n... [{path} 的 diff 已截断]\n"
            truncated = True
        if total + len(piece) > MAX_TOTAL_DIFF_CHARS:
            remain = MAX_TOTAL_DIFF_CHARS - total
            if remain > 200:
                pieces.append(piece[:remain] + "\n... [diff 总量已达上限，后续省略]\n")
            truncated = True
            break
        pieces.append(piece)
        total += len(piece)

    return "".join(pieces), truncated


# ==========================================================================
# 测试 / benchmark 输出解析
# 这里抽出来的每个数字都会进 Verified Facts，因此必须是确定性匹配。
# ==========================================================================
_METRIC_PATTERNS = [
    # (指标名, 正则, 说明)
    ("duration", re.compile(
        r'(?:took|elapsed|耗时|用时|in)\s*[:：]?\s*(\d+(?:\.\d+)?)\s*(ms|s|sec|secs|seconds|秒)',
        re.IGNORECASE), "耗时"),
    ("tests_passed", re.compile(
        r'(\d+)\s*(?:tests?\s*)?(?:passed|ok|通过)', re.IGNORECASE), "通过数"),
    ("tests_failed", re.compile(
        r'(\d+)\s*(?:tests?\s*)?(?:failed|failures?|失败)', re.IGNORECASE), "失败数"),
    ("tests_total", re.compile(
        r'(?:ran|total|共)\s*(\d+)\s*tests?', re.IGNORECASE), "总数"),
    ("throughput", re.compile(
        r'(\d+(?:\.\d+)?)\s*(?:tok/s|tokens?/s|it/s|ops/s)', re.IGNORECASE), "吞吐"),
    ("percentile", re.compile(
        r'p(50|90|95|99)\s*[:=]?\s*(\d+(?:\.\d+)?)\s*(ms|s)?', re.IGNORECASE), "分位延迟"),
    ("version", re.compile(
        r'\b(\d+\.\d+\.\d+(?:[-+][\w.]+)?)\b'), "版本号"),
    ("device", re.compile(
        r'\b(NPU|GPU\.\d+|GPU|CPU)\b'), "设备"),
]


def _parse_test_log(path: Path) -> dict:
    """读取测试/benchmark 输出，抽取确定性指标与带行号的锚点。"""
    raw = path.read_text(encoding="utf-8", errors="replace")
    lines = raw.splitlines()

    metrics: dict[str, list[dict]] = {}
    for name, pattern, label in _METRIC_PATTERNS:
        hits = []
        for lineno, line in enumerate(lines, start=1):
            for m in pattern.finditer(line):
                hits.append({
                    "value": m.group(0).strip(),
                    "groups": [g for g in m.groups() if g is not None],
                    "line": lineno,
                    "label": label,
                    # 锚点：文件:行号，读者可直接跳过去核对
                    "anchor": f"{path.name}:{lineno}",
                })
                if len(hits) >= 8:
                    break
            if len(hits) >= 8:
                break
        if hits:
            metrics[name] = hits

    excerpt = raw
    truncated = False
    if len(excerpt) > MAX_TEST_LOG_CHARS:
        # 保留头尾：头部通常是环境信息，尾部通常是结论
        head = excerpt[: MAX_TEST_LOG_CHARS // 2]
        tail = excerpt[-MAX_TEST_LOG_CHARS // 2:]
        excerpt = head + "\n... [中间省略] ...\n" + tail
        truncated = True

    return {
        "path": str(path),
        "name": path.name,
        "lines": len(lines),
        "excerpt": excerpt,
        "excerpt_truncated": truncated,
        "metrics": metrics,
        "has_metrics": bool(metrics),
    }


# ==========================================================================
# 主入口
# ==========================================================================
def collect(cwd: Path, commits: int | None = None,
            test_log: Path | None = None) -> dict:
    """采集证据包。

    commits=None  → 分析工作区相对 HEAD 的未提交变更（含已暂存）
    commits=N     → 分析最近 N 个提交
    """
    repo = _repo_info(cwd)
    root = Path(repo["root"])

    anchors: list[dict] = []
    commit_list: list[dict] = []

    if commits and commits > 0:
        mode = "commits"
        n = min(commits, max(repo["commit_count"], 1))
        rev = f"HEAD~{n}..HEAD" if repo["commit_count"] > n else "HEAD"

        # 提交元信息：用 \x1f 分隔字段、\x1e 分隔记录，避免正文换行干扰解析
        fmt = "%H%x1f%h%x1f%an%x1f%ad%x1f%s%x1f%b%x1e"
        log_out = _git(root, "log", f"-n{n}", f"--format={fmt}", "--date=iso",
                       check=False)
        for rec in log_out.split("\x1e"):
            rec = rec.strip("\n")
            if not rec.strip():
                continue
            parts = rec.split("\x1f")
            if len(parts) < 5:
                continue
            sha, short, author, date, subject = parts[:5]
            body = parts[5] if len(parts) > 5 else ""
            commit_list.append({
                "sha": sha, "short": short, "author": author,
                "date": date, "subject": subject, "body": body.strip(),
            })
            anchors.append({"kind": "commit", "ref": short,
                            "detail": subject[:80]})

        if repo["commit_count"] > n:
            numstat = _git(root, "diff", "--numstat", rev, check=False)
            namestat = _git(root, "diff", "--name-status", rev, check=False)
            diff_full = _git(root, "diff", rev, check=False)
        else:
            # 仓库提交数不足，退化为看全部历史的引入内容
            numstat = _git(root, "show", "--numstat", "--format=", "HEAD", check=False)
            namestat = _git(root, "show", "--name-status", "--format=", "HEAD",
                            check=False)
            diff_full = _git(root, "show", "--format=", "HEAD", check=False)
    else:
        mode = "working-tree"
        # 相对 HEAD 的 diff 同时覆盖已暂存与未暂存的改动
        numstat = _git(root, "diff", "HEAD", "--numstat", check=False)
        namestat = _git(root, "diff", "HEAD", "--name-status", check=False)
        diff_full = _git(root, "diff", "HEAD", check=False)
        anchors.append({"kind": "commit", "ref": repo["head_short"],
                        "detail": "变更基线 HEAD"})

    nums = _parse_numstat(numstat)
    stats_map = _parse_name_status(namestat)

    files = []
    total_added = total_deleted = 0
    for path, (added, deleted) in nums.items():
        code = stats_map.get(path, "M")
        files.append({
            "path": path,
            "status": code,
            "status_cn": _STATUS_CN.get(code, code),
            "added": added,
            "deleted": deleted,
        })
        total_added += added
        total_deleted += deleted

    # 未跟踪文件：不进 diff，但要让作者知道它们存在（可能是本次决策的一部分）
    untracked = []
    if mode == "working-tree":
        ut = _git(root, "ls-files", "--others", "--exclude-standard", check=False)
        untracked = [ln for ln in ut.splitlines() if ln.strip()][:20]

    chunks = _split_diff_by_file(diff_full)
    for path, body in list(chunks.items())[:MAX_FILES_DETAIL]:
        anchors.extend(_hunk_anchors(path, body)[:3])

    diff_text, diff_truncated = _truncate_diff(chunks)

    test_info = None
    if test_log is not None:
        p = test_log if test_log.is_absolute() else (cwd / test_log)
        if not p.is_file():
            raise FileNotFoundError(f"测试日志不存在：{p}")
        test_info = _parse_test_log(p)
        anchors.append({"kind": "test", "ref": test_info["name"],
                        "detail": f"{test_info['lines']} 行输出"})

    empty = (not files) and (not untracked) and (not commit_list)

    return {
        "repo": repo,
        "mode": mode,
        "commits": commit_list,
        "files": sorted(files, key=lambda f: -(f["added"] + f["deleted"])),
        "untracked": untracked,
        "diff_text": diff_text,
        "diff_truncated": diff_truncated,
        "diff_total_bytes": len(diff_full),
        "stats": {
            "files": len(files),
            "added": total_added,
            "deleted": total_deleted,
        },
        "test_log": test_info,
        "anchors": anchors,
        "empty": empty,
    }
