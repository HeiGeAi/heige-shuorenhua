# 说人话 skill（heige-shuorenhua）

黑哥自己在用的中文润色 skill。把 AI 写好的文案改成人话：删空话、套话、模板句和 AI 腔，不增不减事实，只改说法。

它专门抓两类毛病：

- **格式上的**：破折号、每段最后一句总结升华、一句话里塞好几个数字。
- **说话套路**：不是什么而是什么这种先否定再肯定的句子，首先其次、综上所述、值得注意的是这类套话。

带一个检查脚本 `lint.py`，有硬伤直接报错，错误清零才算改完。

改造自歸藏的 [op7418/Humanizer-zh](https://github.com/op7418/Humanizer-zh)（MIT），和上游的差异见 `references/patterns.md` 开头。

## 安装

Claude Code：

```bash
git clone https://github.com/HeiGeAi/heige-shuorenhua.git ~/.claude/skills/heige-shuorenhua
```

Codex 或其他支持 skill 的 Agent，放到对应的 skills 目录即可，例如 `~/.codex/skills/heige-shuorenhua`。

装好后跟 AI 说「用说人话过一遍这篇稿子」就行。只想跑检查脚本（Python 3，无第三方依赖）：

```bash
python3 ~/.claude/skills/heige-shuorenhua/scripts/lint.py 你的稿子.md --mode article   # 口播用 koubo，字幕用 subtitle
```

## 目录

| 文件 | 用途 |
|---|---|
| `SKILL.md` | skill 本体：优先级、硬规则、改法、流程、交付 |
| `references/patterns.md` | 31 条模式的完整说明和改写前后例子 |
| `scripts/lint.py` | 硬规则自动检查，`--mode article / koubo / subtitle` |
| `scripts/check_structure.py` | 比对 Markdown 改前改后，确认标题、代码、链接、表格没动 |
| `tests/fixtures/` | 18 条边界案例和结构测试样本 |

## 按自己的规则改

硬规则表在 `SKILL.md`，禁用词表在 `scripts/lint.py`，换成你自己的规则就行。

## 致谢与许可证

- 上游：[op7418/Humanizer-zh](https://github.com/op7418/Humanizer-zh)，作者歸藏，MIT；上游又参考了 blader/humanizer 和 hardikpandya/stop-slop。
- 本项目：MIT，见 [LICENSE](LICENSE)。

## 版本

- v1.1.0（2026-10-26）：首次公开。加入作者自我点评句检查。
- v1.0.0（2026-10-17）：由 Humanizer-zh 2026-09-23 修订版改造，加入硬规则表、账号口吻隔离、口播和字幕模式、lint.py。
