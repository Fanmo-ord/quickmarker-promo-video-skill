---
name: quickmarker-promo-video-skill
description: >-
  面向英语教师和教培机构宣传的英语批改助手视频自动化 Skill。负责环境准备、素材盘点、
  差异化选题、脚本与样帧、主片生成、剪映旁白字幕混音、封面和交付整理。适用于日更短视频、
  产品推广视频、QuickMarker 视频和选题池维护。
license: MIT
metadata:
  author: Fanmo-ord
  version: 1.2.3
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

# 英语批改助手宣传视频流水线

作为英语批改助手的 AI 视频运营，直接完成环境准备、素材盘点、选题、文案、制作、剪映后期和交付整理。用户参与创意确认、成片人工验收和发布决策。

本 Skill 是编排层：负责业务规则、阶段顺序、文件管理和审批状态。视觉样帧与主片由 `ai-promo-video-maker` 实际执行；旁白、字幕、混音、封面和草稿由 `jianying-editor-skill` 实际执行。进入对应阶段时，先加载依赖 Skill 的 `SKILL.md` 及其要求的工作规范，并使用其模板、脚本或 API 产出文件。

状态机对这三个制作阶段执行来源校验：视觉样帧、含二维码主片、剪映后期。推进时必须登记匹配的依赖 Skill、实际入口文件和存在的产物；视觉阶段还必须登记 3 个不同样帧。缺少执行证据时不得推进。

## 调用示例

```text
/quickmarker-promo-video-skill 做今天的英语批改助手宣传视频
/quickmarker-promo-video-skill 初始化环境
/quickmarker-promo-video-skill 查看选题池
/quickmarker-promo-video-skill 用现有素材做一条 45 秒抖音视频
/quickmarker-promo-video-skill 继续上次中断的项目
```

## 执行标准

1. 工具和素材采用免费开源、免费可商用或用户已有授权的来源。
2. `ai-promo-video-maker` 负责画面、节奏、转场和二维码片尾。
3. `jianying-editor-skill` 负责自然旁白、单层底部字幕、混音、封面和剪映交付。
4. 主片包含至少 5 秒的完整可扫描二维码和明确 CTA。
5. 最终画面保持 9:16 原始尺寸；旁白字幕位于底部并与声音时间轴一致。
6. macOS 交付可编辑剪映草稿，由用户点击导出；Windows 自动导出并返回成片文件位置。
7. 姓名、成绩、手机号、学校和作业内容经过隐私检查后进入制作与公开交付。
8. 每次制作使用独立项目目录和递增版本号，状态文件支持中断续作。
9. 发布动作在用户明确确认后执行。
10. 文件创建和归档遵循 `references/file-management.md`。

## 启动命令

```bash
python3 <SKILL_ROOT>/scripts/run_pipeline.py --workspace "<用户工作区>" start --install
```

由 AI 执行该命令，并根据返回的 `next_action` 推进任务。

## 工作流

```text
环境与依赖检查
→ 素材、隐私与版权盘点
→ 产品定位与官网信息读取
→ 选题池差异化检查
→ 脚本、镜头表与平台文案
→ ai-promo-video-maker 生成 3 套差异化视觉方向与样帧，用户选择
→ ai-promo-video-maker 生成含二维码片尾的主片
→ 二维码可扫描性验证
→ jianying-editor-skill 完成旁白、字幕、混音和封面
→ Windows 自动导出 / macOS 用户导出
→ 交付清单与用户人工验收
→ 用户确认发布
```

## 阶段要求

### 初始化与素材

- 创建 `00-项目管理` 至 `05-自动化工具`、`90-归档` 标准目录。
- 新增素材先进入 `03-内容运营/01-素材收集/待整理/`。
- 产品界面静帧完成筛选和语义化命名后归入 `02-素材库/01-产品截图/`。
- 读取仓库预置资料并盘点用户本地素材。
- 优先恢复最近的未完成项目。

### 选题与方案

- 从 `03-内容运营/06-状态记录/topic-pool.json` 读取已有选题。
- 通过受众痛点、使用场景、产品能力或证据形式形成差异化角度。
- 默认受众为英语教师和教培机构。
- 每个项目记录平台、标题、角度、钩子、卖点、素材、脚本、日期和状态。

### 创意确认

- 实际调用 `ai-promo-video-maker`，提供 3 套构图、配色和动效语言明显不同的可查看样帧，并标注推荐项。
- 提供 BGM、旁白音色和节奏建议。
- 记录视觉、声音、封面和发布四个审批结果。

### 主片与剪映

- 默认画布为 1080×1920、9:16，并根据平台设置安全区和时长。
- 主片完成画面、转场、节奏和二维码片尾。
- 剪映草稿完成旁白、底部字幕、BGM 混音和封面。
- 业务项目脚本保存在用户工作区。

### 交付

- 成片保存到 `04-视频项目/03-成片/<project-id>/`。
- `delivery-manifest.json` 汇总草稿、MP4、封面、脚本、平台文案和待人工验收状态。

## 参考资料

- 工作流：`references/workflow.md`
- 创意审批：`references/creative-approval-gates.md`
- 平台导出：`references/platform-export.md`
- 产品定位：`references/product-positioning.md`
- 来源：`references/source-links.md`
- 文件管理：`references/file-management.md`
- 故障处理：`references/troubleshooting.md`
