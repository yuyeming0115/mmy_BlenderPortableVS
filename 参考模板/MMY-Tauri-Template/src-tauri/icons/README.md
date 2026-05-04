# 图标说明

此目录应包含应用图标文件，用于打包。

需要准备以下图标：

| 文件 | 尺寸 | 说明 |
|------|------|------|
| `icon.png` | 512x512 | 主图标（用于标题栏、托盘） |
| `32x32.png` | 32x32 | Windows 小图标 |
| `128x128.png` | 128x128 | macOS/通用 |
| `128x128@2x.png` | 256x256 | macOS Retina |
| `icon.icns` | - | macOS 图标包 |
| `icon.ico` | - | Windows 图标包 |

## 生成图标

### 方法 1：使用 Tauri CLI
```bash
# 准备一个 512x512 的 PNG 图标放在 public/icon.png
npm run tauri icon public/icon.png
```

这会自动生成所有需要的图标格式。

### 方法 2：手动准备
- `.icns`: 使用 macOS 的 `iconutil` 或在线工具
- `.ico`: 使用 Windows 工具或在线转换网站