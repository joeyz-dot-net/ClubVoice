# 📱 ClubVoice PWA 支持

## 功能概述

ClubVoice 现已完全支持 PWA (Progressive Web App)，提供原生应用级别的体验：

### ✨ 核心功能

- **📲 安装到主屏幕** - 像原生应用一样在主屏幕上显示
- **🔄 离线缓存** - 静态资源离线可用
- **🎵 后台播放** - 支持 iOS/Android 后台音频播放
- **🎮 锁屏控制** - 在控制中心/锁屏界面控制播放
- **⚡ 快速启动** - Service Worker 加速页面加载
- **🔔 推送通知** - 支持消息推送（可扩展）

## 📱 安装步骤

### iOS Safari

1. 打开 ClubVoice 网页
2. 点击底部「分享」按钮
3. 选择「添加到主屏幕」
4. 点击「添加」

### Android Chrome

1. 打开 ClubVoice 网页
2. 点击浏览器菜单（三个点）
3. 选择「添加到主屏幕」或「安装应用」
4. 确认安装

### Windows/Mac Chrome

1. 打开 ClubVoice 网页
2. 地址栏右侧会显示安装图标 ⊕
3. 点击安装图标
4. 确认安装

## 🎯 使用体验

安装后，ClubVoice 将：

- ✅ **独立窗口运行** - 无浏览器地址栏和按钮
- ✅ **自动更新** - Service Worker 自动更新缓存
- ✅ **快速启动** - 从主屏幕图标直接启动
- ✅ **全屏体验** - 更沉浸的使用体验
- ✅ **后台支持** - 切换应用或锁屏时音频继续播放

## 🧪 测试功能

访问 `/static/pwa-test.html` 查看 PWA 功能测试面板：

- 检测 PWA 支持状态
- 查看已缓存资源
- 测试 Service Worker
- 查看所有图标尺寸
- 手动安装/卸载 PWA

## 📦 包含资源

### Manifest 文件
- `static/manifest.json` - PWA 配置清单

### Service Worker
- `static/sw.js` - 后台工作线程

### 图标资源
- `icon-72.png` (72×72) - 小图标
- `icon-96.png` (96×96) - 小图标
- `icon-128.png` (128×128) - 标准图标
- `icon-144.png` (144×144) - Windows 磁贴
- `icon-152.png` (152×152) - iOS 图标
- `icon-192.png` (192×192) - Android 图标
- `icon-384.png` (384×384) - 高清图标
- `icon-512.png` (512×512) - 超高清图标
- `favicon.ico` - 浏览器标签图标

## 🔧 开发者信息

### Service Worker 策略

- **静态资源** - 缓存优先（Cache First）
- **动态内容** - 网络优先（Network First）
- **Socket.IO** - 不缓存，直接通过网络
- **离线后备** - 网络失败时返回缓存

### 缓存管理

- **主缓存** - `clubvoice-v1.0.0` 存储静态资源
- **运行时缓存** - `clubvoice-runtime` 存储动态内容
- **自动清理** - 更新时删除旧版本缓存

### 更新机制

1. Service Worker 检测到更新
2. 下载新版本资源
3. 后台安装完成
4. 用户刷新页面后激活新版本

## 📊 浏览器兼容性

| 功能 | Chrome | Safari | Firefox | Edge |
|------|--------|--------|---------|------|
| Service Worker | ✅ | ✅ | ✅ | ✅ |
| Manifest | ✅ | ✅ | ✅ | ✅ |
| 安装到主屏幕 | ✅ | ✅ | ⚠️ | ✅ |
| MediaSession | ✅ | ✅ | ✅ | ✅ |
| 后台音频 | ✅ | ✅ | ✅ | ✅ |
| 推送通知 | ✅ | ❌ | ✅ | ✅ |

> ⚠️ Firefox 不支持自动安装提示，需手动从菜单添加

## 🚀 性能优势

- **首次加载** - 正常网络速度
- **再次访问** - 从缓存加载，极速启动
- **离线访问** - 静态页面可离线使用
- **更新延迟** - < 5 秒检测并应用更新

## 🐛 故障排除

### PWA 无法安装

1. 确保使用 HTTPS 或 localhost
2. 检查 manifest.json 是否正确
3. 确认 Service Worker 已注册
4. 查看浏览器控制台错误信息

### Service Worker 未更新

1. 关闭所有 ClubVoice 标签页
2. 打开浏览器开发者工具
3. Application → Service Workers
4. 点击 "Unregister" 注销
5. 刷新页面重新注册

### 音频后台不播放

1. 确认已点击"开始收听"按钮
2. 检查 MediaSession API 是否支持
3. iOS 需要添加到主屏幕获得最佳体验
4. 查看控制台的 AudioContext 状态

## 📝 维护说明

### 更新图标

```bash
python tools/generate_icons.py
```

### 更新缓存版本

编辑 `static/sw.js`，修改：

```javascript
const CACHE_NAME = 'clubvoice-v1.0.1'; // 递增版本号
```

### 清理旧缓存

Service Worker 会自动清理旧版本，或手动：

```javascript
// 浏览器控制台
caches.keys().then(keys => keys.forEach(key => caches.delete(key)));
```

## 🎉 总结

通过 PWA 支持，ClubVoice 提供了：

- ✅ **更好的用户体验** - 像原生应用一样流畅
- ✅ **更强的后台能力** - iOS Safari 后台播放
- ✅ **更快的加载速度** - Service Worker 缓存加速
- ✅ **更低的流量消耗** - 静态资源只加载一次

**立即安装 ClubVoice PWA，享受原生应用级别的语音通信体验！**
