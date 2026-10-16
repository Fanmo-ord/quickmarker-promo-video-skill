# 平台导出

## macOS

`jianying-editor-skill` 生成、修复并打开剪映草稿。AI 验证草稿可打开、素材在线、画布为竖屏、主画面尺寸正确、底部字幕单层显示，然后提示用户点击“导出”。

用户完成导出并人工验收成片；AI 提供草稿路径和交付清单。

## Windows

`jianying-editor-skill` 生成草稿并执行自动导出。AI 返回成片文件位置并生成交付清单，成片由用户人工验收。

## 输出目录

```text
04-视频项目/03-成片/<project-id>/<project-id>.mp4
```

每个版本同时保存封面、脚本、平台文案和 `delivery-manifest.json`。交付清单记录文件位置、制作信息和 `pending_manual_review` 状态。
