# SoloCore 图片资源目录

本目录用于存放 README.md 和项目文档中使用的图片资源。

## 📁 目录结构

```
assets/images/
├── logo/              # Logo 和品牌相关图片
│   ├── solocore-logo.png          # 项目主 Logo
│   ├── solocore-logo-dark.png     # 深色版本 Logo
│   └── solocore-icon.png          # 应用图标
│
├── screenshots/       # 系统截图和演示图片
│   ├── dashboard.png              # 主界面截图
│   ├── textloom-demo.png          # TextLoom 功能演示
│   ├── video-generation.png       # 视频生成过程
│   └── workflow.png               # 工作流程图
│
└── contact/          # 个人联系方式相关图片
    ├── wechat-qrcode.png          # 微信二维码
    ├── bilibili-qrcode.png        # B站二维码
    ├── douyin-qrcode.png          # 抖音二维码
    └── gongzhonghao-qrcode.png    # 公众号二维码
```

## 📝 使用方法

在 README.md 中引用图片时，使用相对路径：

```markdown
# Logo
![SoloCore Logo](assets/images/logo/solocore-logo.png)

# 截图
![系统截图](assets/images/screenshots/dashboard.png)

# 联系方式
<img src="assets/images/contact/wechat-qrcode.png" width="200" alt="微信二维码">
```

## 🎨 图片规范建议

### Logo 和图标
- **格式**: PNG（带透明背景）
- **尺寸**:
  - Logo: 建议 400x100 或 800x200
  - Icon: 建议 512x512 或 1024x1024
- **文件大小**: < 200KB

### 截图
- **格式**: PNG 或 JPG
- **尺寸**: 建议宽度 1200-1920px
- **文件大小**: < 500KB（可使用压缩工具）
- **建议**: 使用高清截图，必要时添加标注或说明

### 二维码
- **格式**: PNG
- **尺寸**: 建议 500x500 或 800x800
- **文件大小**: < 100KB
- **建议**: 保持高清晰度，方便扫描

## 🔧 图片优化工具推荐

- **在线压缩**: TinyPNG (https://tinypng.com/)
- **批量处理**: ImageMagick
- **二维码生成**: 草料二维码 (https://cli.im/)

---

💡 **提示**: 将图片放入对应的子目录中，保持项目资源的整洁有序。
