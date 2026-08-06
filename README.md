# invoice-download

Aether Agent Skill：从国家税务总局电子发票服务平台的二维码交付页面自动下载电子发票 PDF。

## 功能

- 解码电子发票二维码链路，定位 PDF 交付下载地址
- 在浏览器中拦截动态生成的下载链接（规避 App 内下载拦截）
- 携带登录态（Cookie）请求并保存 PDF 发票文件
- 从 PDF 中提取票号、金额、开票日期、销售方等元信息，自动重命名文件

## 目录结构

```
invoice-download/
├── SKILL.md                  # 技能主文件（完整操作流程与注意事项）
├── references/
│   └── intercept.js          # 浏览器下载链接拦截脚本
└── scripts/
    ├── decode_qrcode.py      # 二维码解码脚本（中心裁剪 + Otsu 二值化预处理）
    └── download_pdf.py       # PDF 下载脚本（携带 Cookie）
```

## 安装

通过 Aether 技能管理器从本仓库安装：

```
https://github.com/Arisemoss/invoice-download-skill
```

## 使用

向 Agent 提供包含发票二维码的截图，Agent 将自动执行：

1. 读取并解码二维码，解析出真实 PDF 交付地址
2. 启用浏览器下载链接拦截，获取完整下载 URL
3. 携带已登录的 Cookie 请求并下载 PDF
4. 校验文件为有效发票后，按元信息重命名并存放到输出目录