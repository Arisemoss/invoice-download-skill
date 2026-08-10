# invoice-download

Aether Agent Skill：从国家税务总局电子发票服务平台的二维码交付页面自动下载电子发票 PDF（**支持多省份**）。

> ✅ **已通过真实发票实战验证（2026-08-07）**：使用本 Skill 成功下载了一张真实电子发票 PDF（发票号码 INVOICE_NUMBER_PLACEHOLDER，146KB，校验完整）。验证细节见下方「实战验证记录」。

## 功能

- **多省份支持**：自动识别四川、广东、浙江、北京、上海、江苏、山东等省份的税务平台
- 解码电子发票二维码，解析出 PDF 交付页面地址
- 提取页面 Vue 组件中的发票元信息与校验码（fphm / jym / kprq / 购买方 / 销售方 / 金额等）
- **通过 Vue 组件方法 `openEwmjf` 直接触发下载**（替代不可靠的 `<a>.click()` 拦截，规避页面 JS 混淆与 App 内下载拦截）
- 从 `network_requests` 捕获真实下载请求 URL（`/kpfw/fpjfzz/v1/exportDzfpwjEwm`）
- 携带登录态（Cookie）请求并下载 PDF 发票文件，校验 `%PDF-` 文件头完整性
- 按票号、购买方、金额等元信息自动重命名，归档到工作区

## 支持省份

| 省份 | 域名格式 | 配置状态 |
|------|----------|----------|
| 四川 | `dppt.sichuan.chinatax.gov.cn` | ✅ 已验证 |
| 广东 | `dppt.guangdong.chinatax.gov.cn` | ✅ 已配置 |
| 浙江 | `dppt.zhejiang.chinatax.gov.cn` | ✅ 已配置 |
| 北京 | `dppt.beijing.chinatax.gov.cn` | ✅ 已配置 |
| 上海 | `dppt.shanghai.chinatax.gov.cn` | ✅ 已配置 |
| 江苏 | `dppt.jiangsu.chinatax.gov.cn` | ✅ 已配置 |
| 山东 | `dppt.shandong.chinatax.gov.cn` | ✅ 已配置 |

> 📍 **自动识别**：系统会从二维码URL中自动识别省份，无需手动指定。如需添加新省份，只需在 `references/province_config.json` 中添加配置即可。

## 目录结构

```
invoice-download/
├── SKILL.md                      # 技能主文件（完整操作流程与注意事项）
├── README.md                     # 本说明文档
├── references/
│   ├── trigger_download.js       # Vue 组件方法触发下载脚本（实战验证版）
│   └── province_config.json      # 多省份配置文件（新增）
└── scripts/
    ├── decode_qrcode.py          # 二维码解码脚本（支持多省份识别）
    └── download_pdf.py           # PDF 下载脚本（携带 Cookie，默认输出到工作区）
```

## 安装

通过 Aether 技能管理器从本仓库安装：

```
https://github.com/Arisemoss/invoice-download-skill
```

## 使用

向 Agent 提供包含发票二维码的截图，Agent 将自动执行：

1. 解码二维码，解析出 PDF 交付页面地址（自动识别省份）
2. 用浏览器打开交付页，从 Vue 组件提取 `formData`（含校验码 jym、发票号 fphm 等）
3. 读取 `document.cookie` 获取登录态 Cookie
4. **在组件上下文调用 `openEwmjf` 方法触发下载**，从 `network_requests` 捕获真实下载 URL
5. 携带 Cookie 下载 PDF，校验文件头
6. 按元信息重命名并存放到工作区

**多省份使用示例：**
```bash
# 解码二维码（自动识别省份）
python3 decode_qrcode.py invoice_qr.jpg

# 手动指定省份（可选）
python3 decode_qrcode.py invoice_qr.jpg --province guangdong
```

## 实战验证记录

**验证日期**：2026-08-07

**验证结果**：✅ 成功

| 步骤 | 方法 | 结果 |
|------|------|------|
| 二维码解码 | 中心裁剪 + Otsu 二值化 | ✅ 解析出交付 URL |
| 省份识别 | 域名匹配 `dppt.sichuan.chinatax.gov.cn` | ✅ 自动识别为四川 |
| 提取数据源 | Vue 组件 `formData` + `document.cookie` | ✅ jym=VALIDATION_CODE_PLACEHOLDER、cookie 完整 |
| 触发下载 | 组件方法 `openEwmjf` 直接调用 | ✅ 返回对象、触发请求 |
| 捕获 URL | `network_requests` 过滤 `exportDzfpwjEwm` | ✅ 拿到完整下载地址 |
| 下载 PDF | `download_pdf.py` 携带 Cookie | ✅ 143KB，`%PDF-1.7` 开头 |
| 归档 | 按元信息重命名到工作区 | ✅ 完成 |

**验证发票**：
- 发票号码：INVOICE_NUMBER_PLACEHOLDER
- 开票日期：INVOICE_DATETIME_PLACEHOLDER
- 价税合计：AMOUNT_PLACEHOLDER
- 购买方：BUYER_COMPANY_PLACEHOLDER
- 销售方：SELLER_COMPANY_PLACEHOLDER
- 省份：四川

### 关键经验（踩坑记录）

1. **❌ 不要用 `<a>.click()` 拦截**：该平台页面 JS 混淆，下载由 Vue 组件方法 `openEwmjf` 触发，拦截 click 会返回空数组。必须用「组件方法直接调用 + network_requests 捕获」。
2. **二维码解码**：直接解码易失败，务必中心裁剪 + Otsu 二值化预处理。
3. **Cookie 必需**：下载 API 需要登录态，需携带 `document.cookie` 读到的非 httpOnly cookie。
4. **仅下载 PDF**：触发时 `Wjgs=PDF`，不下载 OFD / XML。
5. **文件校验**：PDF 以 `%PDF-` 开头、`%%EOF` 结尾，下载后必须校验。
6. **页面 JS 混淆**：直接读源码不可行，可下载主 JS 包后 grep 关键端点字符串。
7. **多省份扩展**：所有省份使用相同的下载端点路径，只需替换域名即可。添加新省份只需更新 `province_config.json`。

## 更新日志

### v1.1.0 (2026-08-07)
- ✨ 新增多省份支持（四川、广东、浙江、北京、上海、江苏、山东）
- ✨ 新增省份自动识别功能
- ✨ 新增 `references/province_config.json` 配置文件
- 📝 更新 `decode_qrcode.py`，支持 `--province` 参数
- 📝 更新 SKILL.md，添加多省份使用说明
- ✅ 实战验证通过（四川税务平台）

### v1.0.0 (2026-08-07)
- 🎉 初始版本
- ✅ 支持四川税务电子发票平台
- ✅ 实战验证通过
