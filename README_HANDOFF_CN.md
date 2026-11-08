# AntWorld v0.8 — 交给 Codex 前的完整设计基线

## 你拿到了什么

- `docs/`：v0.7 的全部历史设计 + v0.8 工程契约。用户已经确定和仍待验证的内容明确分开。
- `AGENTS.md`：Codex 在项目仓库里应遵守的规则。
- `CODEX_START_HERE.md`：阅读顺序与执行范围。
- `codex_tasks/S0_KICKOFF_PROMPT.md`：**直接粘贴给 Codex 的首次任务**，只实施 S0。
- `contracts/antworld_c_api_v1.h`：C++ 与 C# 的 API 草案（非游戏实现）。
- `schemas/` 和 `scenarios/`：有 Schema 和工程测试场景，标记为非科学标定。
- `MANIFEST_SHA256.md`：文件校验，保证归档在传递后可检查。

## 如何开始

1. 将本归档解压到一个新的 **AntWorld 项目仓库根目录**（不是只把单个 Prompt 粘贴给 Codex）。
2. 用 Git 初始化/提交这份设计基线，并打开这个项目目录给 Codex。
3. 请 Codex 阅读 `AGENTS.md` 和 `CODEX_START_HERE.md`。
4. 将 `codex_tasks/S0_KICKOFF_PROMPT.md` 全文复制给 Codex；**首次只执行 S0**。
5. Codex 完成后，检查它输出的 `S0_RESULTS.md`、实际测试记录和改动文件，通过后再决定进入 S1。

## 哪些事情仍未完成？

**还没有开发游戏代码**，也没有运行蚂蚁行为、Unity 或 Game Master 测试。没有完成的真实生物参数标定、具体 SDF 原语/数值精度、完整 Agent Harness 选型和多精度性能测量，已明确保留为后续开发/科研任务，而不是隐瞒。

## 与此前版本的关系

v0.8 基于真实存在的 v0.7 设计文件；v0.4–v0.7 原始 ZIP 不需覆盖或删除。建议每次通过 Codex 阶段门禁后，保持 Git 提交记录并更新归档。
