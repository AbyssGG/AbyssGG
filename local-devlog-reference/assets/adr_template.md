# ADR 条目格式参考

本文件是 `local-devlog` 输出格式的说明与样例。实际渲染由
`scripts/devlog_engine.py` 的 `render_adr()` 完成，此处便于人工比对与校准。

## 章节来源对照表

| 章节 | 来源 | 是否经过语言模型 |
| --- | --- | :---: |
| `Status` | 系统日期 | ❌ |
| `Scope` | git 分支 / HEAD / 变更统计 | ❌ |
| `Generated-By` | 实际后端与物理设备 | ❌ |
| `Context` | diff 证据 | ✅ |
| `Decision` | diff 证据 | ✅ |
| `Non-Goals` | diff 证据 | ✅ |
| `Alternatives Considered` | **仅** `--rejected` 用户输入 | ❌ |
| `Verified Facts` | **仅** `--test-log` 的正则匹配 | ❌ |
| `Pitfalls` | diff 证据 | ✅ |
| `Evidence` | git / 日志真实锚点 | ❌ |

四个经过模型的字段只做语言组织；一旦模型写出证据中不存在的性能数字或版本号，
反幻觉守卫会就地替换为「未验证」并在条目末尾报告拦截情况。

## 样例

```markdown
## ADR-0007 用 opaque handle 表示 Backend 资源

- **Status**: 已接受（2026-08-28）
- **Scope**: main @ a1b2c3d4 · 5 文件 +182/-43
- **Generated-By**: isvik / GPU.0 / Qwen2.5-Coder-1.5B-Instruct-int4-ov（本地推理）

### Context

Backend 层此前直接把底层库的裸指针暴露给上层，调用方可以在资源释放后继续
持有该指针，导致释放后使用的问题无法在编译期被发现。

### Decision

改为用不透明整型句柄表示资源，句柄到真实指针的映射由 Backend 内部持有；
上层拿到的句柄失效后再次使用会得到明确的错误码，而不是未定义行为。

### Non-Goals

- 不改变现有的资源生命周期语义，只改变表示方式。
- 不引入引用计数。

### Alternatives Considered

- **继续暴露裸指针** —— 拒绝理由：无法阻止释放后使用，且错误只在运行期暴露。
- **引用计数智能指针** —— 拒绝理由：当前只有单一所有者，引用计数是多余的间接层。

### Verified Facts

| 指标 | 值 | 证据锚点 |
| --- | --- | --- |
| 测试通过 | `38 passed` | `test.txt:41` |
| 耗时 | `elapsed 1.82 s` | `test.txt:43` |

### Pitfalls

现象：句柄表在并发访问下偶发读到已回收的槽位。
根因：回收时只清空了指针，未递增槽位的版本号，导致旧句柄仍能命中。
修复：句柄改为「索引 + 版本号」两字段，版本不匹配直接返回失效错误。

### Evidence

- `commit a1b2c3d` — 引入 opaque handle 表示
- `src/backend/handles.nim:12-88` — 变更区间
- `tests/thandles.nim:1-64` — 变更区间
- `log test.txt` — 41 行输出

---
```

## 「待补充」与「未验证」的区别

| 标记 | 含义 | 处理方式 |
| --- | --- | --- |
| `待补充` | 证据不足以判断，模型拒绝推测 | 作者手工补齐，或补充输入后重跑 |
| `未验证` | 该处本应有实测数字但未提供输出 | 用 `--test-log` 提供真实输出 |

两者出现都是**预期行为**，代表工具没有编造。条目结尾的「未验证字段」计数
大于 0 属于正常情况。
