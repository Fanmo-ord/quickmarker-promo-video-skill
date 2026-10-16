# QuickMarker Promo Video Skill

面向英语批改助手运营人员的 AI 宣传视频自动化 Skill。AI 负责环境准备、素材盘点、差异化选题、脚本、主片、剪映后期和交付验收；用户负责创意确认、macOS 导出和发布决策。

## 工具分工

```text
ai-promo-video-maker：画面、节奏、转场、二维码片尾
jianying-editor-skill：旁白、单层底部字幕、混音、封面、草稿与导出
```

主片包含至少 5 秒的完整可扫描二维码和明确 CTA。剪映阶段完成声音、字幕、封面与最终交付。

## 安装

macOS / Linux：

```bash
git clone https://github.com/Fanmo-ord/quickmarker-promo-video-skill.git
cd quickmarker-promo-video-skill
./scripts/install.sh
```

Windows PowerShell：

```powershell
git clone https://github.com/Fanmo-ord/quickmarker-promo-video-skill.git
cd quickmarker-promo-video-skill
.\scripts\install.ps1
```

首次调用时，AI 会检查 Git、Python、Node.js、FFmpeg 和剪映桌面端，并准备两项免费开源依赖。

## 使用

在支持 Agent Skills 的 AI 中输入：

```text
/quickmarker-promo-video-skill 做今天的英语批改助手宣传视频
```

常用指令：

```text
/quickmarker-promo-video-skill 初始化环境
/quickmarker-promo-video-skill 查看选题池
/quickmarker-promo-video-skill 用现有素材做一条 45 秒抖音视频
/quickmarker-promo-video-skill 继续上次中断的项目
```

AI 会创建标准工作区并使用仓库预置的官网资料、产品截图、二维码和运营定位。新增素材进入待整理区，审核后按最终用途归档。详细规则见 [文件管理规范](references/file-management.md)。

## 平台交付

- Windows：剪映自动导出，AI 验证视频文件、画幅、时长和音轨。
- macOS：AI 生成并打开剪映草稿，用户点击导出后由 AI 验收 MP4。

## 交付标准

- 工具和素材来源为免费开源、免费可商用或用户已有授权。
- 成片使用经过隐私检查的演示数据和产品素材。
- 主画面保持 9:16 完整画幅，字幕位于底部且只有一层。
- 发布动作在用户确认后执行。
- 每个项目保留脚本、镜头表、封面、成片、平台文案和交付清单。

## 开发验证

```bash
python3 scripts/run_pipeline.py --help
python3 scripts/run_evals.py --validate
```

完整工作规范见 [SKILL.md](SKILL.md)，素材使用范围见 [asset-license.md](references/asset-license.md)，贡献方式见 [CONTRIBUTING.md](CONTRIBUTING.md)。
