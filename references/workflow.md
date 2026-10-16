# 完整工作流

## AI 与用户的分工

AI 完成环境检查、依赖安装、素材盘点、选题去重、脚本、样帧、主片、剪映草稿、验证和交付整理。用户只需要：

1. 确认视觉样帧、BGM/声音方向；
2. 确认封面；
3. 在 macOS 剪映中手动点击导出；
4. 决定是否发布。

## 阶段顺序

| 阶段 | AI 产物 | 通过条件 |
|---|---|---|
| 初始化 | 环境报告、素材清单、状态目录 | 两套依赖可发现；素材库和二维码存在 |
| 选题 | 新选题、角度、卖点 | 未与历史标题和角度重复 |
| 脚本 | 旁白稿、镜头表、平台文案 | 卖点有真实产品画面支撑 |
| 创意 | 视觉方向、样帧、BGM/声音建议 | 用户确认样帧与声音方向 |
| 主片 | 竖屏画面母版 | 主片已包含 5 秒以上二维码片尾 |
| 二维码验证 | 片尾证明帧 | 实际扫码成功、无遮挡 |
| 剪映后期 | 旁白、单层底部字幕、混音、封面 | 主画面未缩小、二维码未重复添加 |
| 封面确认 | 封面图 | 用户确认 |
| 导出 | MP4 或待导出的 macOS 草稿 | Windows 文件通过探测；macOS 草稿可打开 |
| 交付 | manifest、视频、封面、文案 | 自动检查和 AI 视觉/听觉复核完成 |

## 状态命令

以下命令由 AI 执行，用户无需手工输入。全局参数必须放在子命令前：

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

`advance` 一次只前进一个阶段。未通过审批门或二维码验证时，它会返回 `needs_approval` 或错误，不会假装继续。

## 主片与剪映的边界

主片不是最终成片。`ai-promo-video-maker` 生成画面、转场、节奏和二维码片尾；为防止字幕重复，主片不烧录最终旁白字幕。剪映导入主片后增加最终旁白、底部字幕、混音和封面。剪映不得再加二维码。

如主片需要按音乐卡点，可以使用已确认的 BGM 作为节奏参考，同时保留无旁白的干净画面母版；最终音量平衡在剪映完成。

## 发布平台适配

- 默认：9:16、1080×1920、30 fps。
- 抖音：开头 1–3 秒直接出现痛点或反差，正文短句，CTA 清楚。
- 视频号：允许稍完整的问题—方案—结果结构。
- 小红书：封面和标题更强调教师场景、清单和可验证收益。
- 平台标题、正文、标签分开保存，不把同一段文案机械复制到所有平台。
- Skill 只准备发布包，不自动发布。

