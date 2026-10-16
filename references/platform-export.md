# 平台导出

## macOS

`jianying-editor-skill` 生成、修复并打开剪映草稿。AI 验证草稿可打开、素材在线、画布为竖屏、主画面尺寸正确、底部字幕单层显示，然后提示用户点击“导出”。

用户导出后，AI 对 MP4 执行最终验证。

## Windows

`jianying-editor-skill` 生成草稿并执行自动导出。完成标准包括：文件存在、时长有效、分辨率正确、音轨存在且文件可解码。

## 输出目录

```text
04-视频项目/03-成片/<project-id>/<project-id>.mp4
```

每个版本同时保存封面、脚本、平台文案和 `delivery-manifest.json`。导出阶段验证主片中的二维码片尾和最终媒体质量。
