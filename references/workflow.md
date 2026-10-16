# 自动化工作流

## 角色

AI 使用本 Skill 编排环境准备、依赖安装、素材盘点、差异化选题、脚本和交付状态；样帧与主片实际调用 `ai-promo-video-maker`，剪映草稿实际调用 `jianying-editor-skill`。

用户确认：

- 视觉样帧
- BGM、旁白音色和节奏
- 封面
- macOS 导出
- 发布

## 阶段

| 阶段 | 主要产物 | 完成条件 |
|---|---|---|
| 初始化 | 环境报告、标准目录、素材清单 | 依赖与素材状态可读 |
| 选题 | 选题记录、角度、卖点、平台 | 与选题池形成明显差异 |
| 脚本 | 口播、镜头表、平台文案 | 时长与素材匹配 |
| 视觉 | 3 套差异化风格方向与样帧 | 用户从 3 套方案中确认一套 |
| 主片 | 画面、转场、节奏、二维码片尾 | 二维码完整且可扫描 |
| 剪映 | 旁白、字幕、混音、封面 | 草稿可打开且素材在线 |
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

## 制作边界

- 主片负责画面、转场、节奏和二维码片尾。
- 剪映负责最终旁白、底部字幕、混音和封面。
- 平台标题、正文和标签分别保存并适配各平台表达。
- 导出后的成片由用户人工验收，发布包经用户确认后进入发布环节。
