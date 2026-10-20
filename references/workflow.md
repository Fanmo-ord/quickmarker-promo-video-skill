# 自动化工作流

## 角色

AI 使用本 Skill 编排环境准备、依赖安装、素材盘点、差异化选题、脚本和交付状态；样帧与主片实际调用 `ai-promo-video-maker`，获批的标志性动效由 Hyperframes 渲染为无声 MP4 后交给 Remotion 合成，剪映草稿实际调用 `jianying-editor-skill`。

用户确认：

- 视觉样帧
- BGM 与画面节奏
- 封面
- macOS 导出
- 发布

## 阶段

| 阶段 | 主要产物 | 完成条件 |
|---|---|---|
| 初始化 | 环境报告、标准目录、素材清单 | 依赖与素材状态可读 |
| 选题 | 3 个差异化候选：标题、角度、卖点 | 用户选择其中 1 个 |
| 脚本 | 规范旁白文本、镜头表、平台文案 | 旁白文本确定且时长与素材匹配 |
| 视觉 | 3 套差异化风格方向与样帧 | 用户从 3 套方案中确认一套 |
| 主片 | 无音轨画面、转场、节奏、二维码片尾 | 二维码可扫描且主体画面通过占比校验 |
| 剪映 | 100% 主视频轨、同步旁白字幕、BGM、封面 | 使用 `add_narrated_subtitles` 且草稿可打开 |
| 导出 | MP4、封面、发布包、交付清单 | 文件位置明确并标记待人工验收 |

## 命令

```bash
python3 scripts/run_pipeline.py --workspace "<工作区>" start --install
python3 scripts/run_pipeline.py --workspace "<工作区>" new \
  --title "45份英语默写怎么快速批完" \
  --angle "教师批改耗时" \
  --selling-point "批量识别与自动批改" \
  --platform douyin
python3 scripts/run_pipeline.py --workspace "<工作区>" status
python3 scripts/run_pipeline.py --workspace "<工作区>" approve --project "<ID>" --gate visual_sample --approved yes
python3 scripts/run_pipeline.py --workspace "<工作区>" approve --project "<ID>" --gate audio_direction --approved yes
python3 scripts/run_pipeline.py --workspace "<工作区>" record-qr --project "<ID>" --passed yes --proof-frame "<图片>" --duration 5
python3 scripts/run_pipeline.py --workspace "<工作区>" advance --project "<ID>" --artifact "<阶段产物>"
```

状态机每次推进一个阶段，并在审批点返回 `needs_approval`。

进入依赖 Skill 执行阶段后，推进命令还需传入 `--executor-skill`、`--skill-entrypoint` 和实际产物路径。视觉阶段用三个 `--sample` 分别登记三套样帧；主片与剪映阶段不传 `--sample`。状态机会核验入口与产物文件是否存在、执行 Skill 是否匹配。

`new` 命令会返回本项目的规范文件路径，并预置创意方案、结构化分镜与交付清单模板。后续产物均写入这些路径。状态机同时校验脚本、主片、剪映草稿、封面、成片和交付清单的产物类型；剪映阶段登记包含 `draft_info.json` 的可编辑草稿目录。

项目进入 `complete` 时，状态机会用导出的成片路径自动把选题池记录改为 `complete`。成片仅标记 `pending_manual_review`，不由 AI 验收或发布。

## 制作边界

- 主片负责画面、转场、节奏和二维码片尾。Hyperframes 仅生成 1 至 3 个无声动效片段，具体契约见 `references/hyperframes-motion.md`。
- 剪映负责最终旁白、底部字幕、混音和封面。
- 任一依赖 Skill 不可用时停止流程并报告；对应阶段以依赖 Skill 的正式产物为准。
- 平台标题、正文和标签分别保存并适配各平台表达。
- 导出后的成片由用户人工验收，发布包经用户确认后进入发布环节。

## 视觉主片合同

1. `ai-promo-video-maker` 输出 `text_free_visual_master`：视觉层只包含背景、装饰视觉、真实产品界面截图和二维码资产。
2. 产品截图内部原有的 UI 文字属于产品素材，可以保留；标题、标签、说明、结语和 CTA 等运营文案由剪映文字轨道承载。
3. Hyperframes 只生成无声视觉动效片段，Remotion 只负责时间轴和视觉合成，两者均不新增运营文字或声音。
4. 二维码在视觉主片中保持静止、完整、可扫描；CTA 作为剪映字幕轨道中的独立口播短句出现。
5. 主片生成后，在 `files.visual_master_contract` 登记实际源码入口，以及开场、主体和二维码片尾至少 3 张验证帧。状态机检查证据文件存在后才允许进入剪映阶段。
6. 产品截图按 100% 主轨画布进行构图，重要 UI 区域避开 `storyboard.subtitle_safe_zone`。

## 旁白字幕合同

1. `files.narration` 是旁白与字幕的唯一文字源，每个非空行对应一个自然停顿短句；单句默认不超过一行字幕的可读宽度。
2. 剪映脚本只调用一次 `add_narrated_subtitles` 生成声音与字幕，不另建独立 TTS 或 SRT 时间轴。
3. 生成后将每段 `text`、实际 `tts_asset` 路径、`start_ms`、`end_ms` 按剪映/TTS 顺序写入 `files.narration_cues`。时间段连续递增，字幕文本顺序与旁白文件逐行一致；状态机同时检查所登记的音频文件确实存在。
4. 字幕锚定画面底部。渲染 PNG 或预览时，先按实际画布计算数值坐标 `canvas_height - subtitle_height - bottom_margin_px`，不把坐标表达式交给滤镜解释。
5. 上游视觉主片不新增运营文字，产品截图的重要 UI 区域避开 `storyboard.subtitle_safe_zone`；主视频轨保持 100% 比例，不为字幕缩放画面。
6. 在每条字幕的时间中点生成验证帧，确认当前只显示该句且不与场景文字重叠；验证结果和证明帧写入 `files.narration_cues` 与交付清单。
7. 以上属于导出前的轨道与布局技术校验；导出后的成片仍由用户人工验收。
