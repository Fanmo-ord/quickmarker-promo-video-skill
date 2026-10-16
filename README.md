# QuickMarker Promo Video Skill

给英语批改助手运营人员使用的 AI 自动化宣传视频 Skill。把这个仓库交给支持 Agent Skills 的 AI，它会负责环境检查、素材盘点、选题去重、脚本、主片、剪映后期和交付验收；用户只确认样帧/声音/封面、在 macOS 点击导出，并决定是否发布。

## 这套流程怎么分工

```text
ai-promo-video-maker：画面、节奏、转场、二维码片尾
jianying-editor-skill：旁白、单层底部字幕、混音、封面、导出/草稿
```

二维码片尾在主片生成时完成，不在剪映阶段重复添加。所有视频片尾至少展示 5 秒可扫描二维码。

## 安装

仓库默认应设为私有，因为预置截图和运营资料可能包含不适合公开分发的信息。

macOS / Linux：

```bash
git clone https://github.com/Fanmo-ord/quickmarker-promo-video-skill.git
cd quickmarker-promo-video-skill
./install.sh
```

Windows PowerShell：

```powershell
git clone https://github.com/Fanmo-ord/quickmarker-promo-video-skill.git
cd quickmarker-promo-video-skill
.\install.ps1
```

安装器只安装本 Skill。第一次调用时，AI 会检测 Git、Python、Node.js、FFmpeg、剪映桌面端，并安装缺失的两个免费开源依赖项目。不会默认购买服务或调用付费 API。

## 使用

在新的 AI 会话中输入：

```text
/quickmarker-promo-video-skill 做今天的英语批改助手宣传视频
```

也可以输入：

```text
/quickmarker-promo-video-skill 初始化环境
/quickmarker-promo-video-skill 查看选题池
/quickmarker-promo-video-skill 继续上次中断的项目
```

AI 会自动创建 `quickmarker-video-workspace/`。新增素材放入其中的 `素材库/incoming/`；即使没有新增素材，AI 也会先使用仓库预置的官网资料、截图、教学视频、二维码和运营定位文档。

## 平台差异

- Windows：AI 可通过剪映自动导出，并验证输出文件。
- macOS：AI 自动生成并打开剪映草稿，用户在剪映中手动点击“导出”，随后 AI 继续验收 MP4。

## 安全边界

- 不自动发布到抖音、视频号、小红书等平台。
- 发布前检查真实姓名、成绩、手机号、学校等个人信息。
- BGM、字体、图片和视频必须免费可商用或已有授权。
- 将本仓库改为公开前，必须完成隐私与版权审核。

## 开发与验证

```bash
python3 scripts/run_pipeline.py --help
python3 scripts/run_evals.py --validate
```

完整约束见 [SKILL.md](SKILL.md)，素材许可见 [ASSET_LICENSE.md](ASSET_LICENSE.md)。

