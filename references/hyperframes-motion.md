# Hyperframes 动效接入

Hyperframes 只负责生成独立的无声动效片段；Remotion 仍是主片时间轴和最终画面合成器，剪映仍负责旁白、字幕、BGM、封面和导出。

## 固定契约

- 版本：`hyperframes@0.8.174`
- 环境：Node.js 22+、`npx`、FFmpeg / ffprobe
- 接入方式：`rendered_clips`
- 输出：1080×1920、30fps、MP4、无音轨
- 每条视频：1 至 3 个标志性动效
- 二维码：二维码本体和可扫描区域不加动效，片尾至少静止 5 秒
- 时间轴：Remotion 的 `timing.json` / 镜头表仍是唯一真相

不要把 Hyperframes 和 Remotion 的运行时放进同一个页面，也不要让 Hyperframes 负责旁白或混音。完整 Hyperframes Agent Skill 会自行组织子代理，不属于本流水线的执行入口；这里只调用固定版本 CLI 和 Catalog。

## 目录

每个视频项目在自己的工程目录内保存：

```text
工程/
├── hyperframes/<clip-id>/       # HTML/CSS/GSAP 源文件
├── public/motion/<clip-id>.mp4  # 交给 Remotion 的无声片段
└── motion-plan.json             # 片段、来源和时间信息
```

不要把业务项目、渲染结果或下载素材写进 Skill 仓库。

## motion-plan.json

创意确认后，把获批片段登记到 `clips`：

```json
{
  "engine": "hyperframes",
  "version": "0.8.174",
  "integration_mode": "rendered_clips",
  "canvas": {"width": 1080, "height": 1920, "fps": 30},
  "rules": {
    "maximum_signature_effects": 3,
    "audio_mode": "silent",
    "qr_region_motion": "none"
  },
  "clips": [
    {
      "id": "hook-title",
      "scene": "hook",
      "start": 0,
      "duration": 4,
      "block": "headline-slam",
      "project": "hyperframes/hook-title",
      "output": "public/motion/hook-title.mp4"
    }
  ]
}
```

`output` 可以是绝对路径，也可以是相对 `motion-plan.json` 所在目录的路径。

## 渲染与校验

```bash
python3 <SKILL_ROOT>/scripts/render_hyperframes_motion.py \
  --project "<工程>/hyperframes/hook-title" \
  --output "<工程>/public/motion/hook-title.mp4" \
  --json
```

脚本会使用锁定版本渲染，并用 ffprobe 拒绝错误尺寸、错误帧率、空文件和带音轨的视频。已有片段可仅校验：

```bash
python3 <SKILL_ROOT>/scripts/render_hyperframes_motion.py \
  --output "<工程>/public/motion/hook-title.mp4" \
  --validate-only --json
```

## 视觉规则

优先选择能解释产品操作的动效：设备框、光标标注、点击、重点高亮、数字增长、图表、卡片堆叠和轻量页面转场。避免大面积粒子、复杂 3D、重度故障和遮挡产品内容的 shader。

创意确认时每个方向除静态样帧外，还要附 3–5 秒动效预览。最终片段进入 Remotion 后，仍执行现有的画面覆盖率、主片无音轨和二维码校验。
