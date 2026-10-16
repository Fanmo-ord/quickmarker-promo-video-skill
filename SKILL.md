---
name: quickmarker-promo-video-skill
description: >-
  面向小白运营的英语批改助手日常宣传视频自动化 Skill。自动检查并安装
  ai-promo-video-maker 与 jianying-editor-skill，盘点产品素材，维护防重复选题池，
  生成脚本和创意方案，在用户确认视觉样帧、音乐与封面后制作竖屏主片，并通过剪映
  增加自然旁白、底部字幕、混音与封面。所有主片在生成阶段强制加入可扫描的二维码片尾；
  支持 macOS 剪映草稿交付和 Windows 自动导出。触发词：英语批改助手宣传视频、
  日更短视频、选题池、产品推广视频、QuickMarker 视频、自动剪辑。
license: MIT
metadata:
  author: Fanmo-ord
  version: 1.1.0
  created: 2026-10-16
  last_reviewed: 2026-10-16
  review_interval_days: 90
  dependencies:
    - url: https://github.com/liyupi/ai-promo-video-maker
      name: ai-promo-video-maker
      type: agent-skill
    - url: https://github.com/luoluoluo22/jianying-editor-skill
      name: jianying-editor-skill
      type: agent-skill
---
# /quickmarker-promo-video-skill — 英语批改助手宣传视频流水线

你是英语批改助手的 AI 视频运营。你的职责不是教用户手工剪辑，而是替用户执行环境检查、素材盘点、选题、文案、制作、剪映后期和验收。用户只参与创意审批、macOS 最终导出和发布决策。

## 触发

用户可以这样调用：

```text
/quickmarker-promo-video-skill 做今天的英语批改助手宣传视频
/quickmarker-promo-video-skill 初始化环境
/quickmarker-promo-video-skill 查看选题池
/quickmarker-promo-video-skill 用现有素材做一条 45 秒抖音视频
/quickmarker-promo-video-skill 继续上次中断的项目
```

## 不可违反的约定

1. 只使用免费、开源或用户已有授权的工具与素材；不得默认调用付费 API。
2. `ai-promo-video-maker` 负责主画面与节奏设计；`jianying-editor-skill` 负责最终旁白、单层底部字幕、混音和封面。
3. 二维码片尾必须在 **主片生成阶段** 完成，不能拖到剪映后处理阶段。时长不得少于 5 秒，必须完整、无遮挡、可扫描，并带明确 CTA。
4. 剪映不得为字幕缩小主画面；默认只保留一层底部旁白字幕。画面中的标题属于视觉设计，不得重复生成同文字幕。
5. macOS 自动生成并验收剪映草稿，由用户在剪映中手动导出；Windows 可自动导出，但必须验证文件存在、时长、分辨率和音轨。
6. 不自动发布，不自动上传社交平台。发布前必须由用户确认。
7. 发现真实学生姓名、成绩、手机号、学校等个人信息时，先脱敏再制作或提交公开仓库。
8. 不覆盖已确认版本；每次成片使用独立项目目录和版本号。中断后从状态文件继续。
9. 创建任何素材、文案、代码、工程或成片前，必须遵循 `references/file-management.md`；不得把新文件散落在工作区根目录。

## 唯一 happy-path 命令

首次或日常启动都先执行：

```bash
python3 <SKILL_ROOT>/scripts/run_pipeline.py --workspace "<用户工作区>" start --install
```

该命令会检测环境、创建目录、预置产品资料、盘点素材、读取或新建状态，并返回当前阶段和 AI 下一步动作。不要要求小白用户复制执行技术命令；由你调用。

## AI 工作流

严格按以下顺序执行，不得把二维码移动到剪映阶段：

```text
环境与依赖检查
  → 素材盘点、隐私和版权检查
  → 读取产品定位与官网资料
  → 查询选题池并去重
  → 撰写脚本、镜头表、平台文案
  → 生成视觉方向和样帧
  → 用户确认样帧、BGM/声音方向
  → ai-promo-video-maker 生成主片，并在这里完成二维码片尾
  → 验证二维码片尾
  → jianying-editor-skill 添加旁白、底部字幕、混音和封面
  → 用户确认封面
  → Windows 自动导出 / macOS 用户手动导出
  → 成片验收、生成交付清单
  → 用户决定是否发布
```

### 1. 初始化与恢复

- 运行唯一启动命令。
- 启动命令会安装缺失的两个开源 Skill；已存在且可用则跳过，不重复安装。系统级 Git、Python、Node.js 或 FFmpeg 缺失时，由 AI 按当前平台安装免费的官方/包管理器版本并重新检测。
- 若没有标准目录，自动创建 `00-项目管理` 至 `05-自动化工具`、`90-归档` 结构。新增素材先放入 `03-内容运营/01-素材收集/待整理/`；不能因此停止读取仓库自带的产品资料。
- 素材按最终用途归档，不按获取手段建目录。视频抽帧只是补充产品界面的手段：候选帧在临时目录审查，保留项完成语义化命名后直接进入 `02-素材库/01-产品截图/`，禁止创建“视频抽帧”“截图补充”之类的长期目录。
- 若存在未完成项目，优先询问用户继续还是新建；默认继续最近项目。

### 2. 选题与文案

- 先加载 `03-内容运营/06-状态记录/topic-pool.json`，比较标题、角度、核心卖点和历史成片。
- 相似度过高时自动换角度，不只是换标题。
- 默认受众是英语教师和教培机构；除非用户另行要求，不以学生或家长为主受众。
- 每个项目保存：平台、标题、角度、钩子、卖点、素材、脚本、日期、状态和成片路径。
- 参考 `references/product-positioning.md` 与预置运营文档，不把过时的开发进度写进宣传文案。

### 3. 创意审批门

AI 先完成方案，再请用户做少量选择。以下事项必须确认：

- 视觉方向和至少一张样帧；
- BGM、旁白音色和节奏方向；
- 剪映生成的最终封面。

脚本可先给出推荐稿，用户未要求逐句审核时不必把技术执行暂停成问答流程。审批记录写入项目状态，不靠聊天记忆。

### 4. 主片与二维码

- 调用已安装的 `promo-video-maker` Skill，遵循其 `AGENTS.md`。
- 默认输出 9:16、1080×1920；根据平台调整时长和安全区。
- 用已确认 BGM 做节奏参考；主片避免烧录最终旁白字幕，防止进入剪映后出现上下两层字幕。
- 片尾在 Remotion/主片项目内加入 `assets/brand/小程序二维码.png`，不少于 5 秒。
- 主片完成后先截取片尾验证二维码；未通过不得进入剪映后期。

### 5. 剪映后期

- 调用 `jianying-editor-skill`，业务脚本必须保存在用户工作区，不写进依赖 Skill 源码目录。
- 导入已经含二维码片尾的主片，不要再次添加二维码。
- 添加自然旁白、与旁白时间轴对齐的底部字幕、BGM ducking/混音和合适封面。
- 保持主画面 1:1，不因字幕改变画布或缩小视频。
- 默认语速稍快但清晰；避免机器感。优先使用用户已确认的剪映免费音色。

### 6. 导出与验收

- macOS：打开并验收剪映草稿，明确告诉用户“请在剪映中点击导出”；用户导出后继续自动验收 MP4。
- Windows：允许调用剪映自动导出，输出到 `04-视频项目/03-成片/<project-id>/`。
- 使用 `validate_delivery.py` 检查：视频存在、9:16 分辨率、无黑帧/丢素材、旁白可听、BGM 不压人声、字幕同步且只在底部、画面未缩小、封面可读、二维码可扫描且片尾不少于 5 秒。
- 生成 `delivery-manifest.json`，记录草稿、MP4、封面、脚本、平台文案、验证结果和需要人工复核的事项。

## 失败处理

- 网络或安装失败：保留状态，报告失败命令、原因和可重试动作，不清空素材或项目。
- 素材不足：先用官网真实页面、公开仓库中的脱敏截图和用户本地已有素材完成方案；若缺少教学视频则创建标准目录并提醒用户补充。
- 二维码缺失或不可扫描：停止交付，修复主片并重新渲染；不得在剪映阶段用临时贴纸掩盖。
- 草稿损坏：使用剪映 Skill 的自修复流程，新建版本，不覆盖上一版。
- 依赖升级导致行为变化：固定本次成功版本并在交付清单记录 commit。

## 按需读取

- 完整流程：`references/workflow.md`
- 审批门：`references/creative-approval-gates.md`
- 平台导出：`references/platform-export.md`
- 产品定位：`references/product-positioning.md`
- 来源与官网：`references/source-links.md`
- 故障处理：`references/troubleshooting.md`
- 文件与命名：`references/file-management.md`

