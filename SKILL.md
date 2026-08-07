---
name: invoice-download
description: >
  从国家税务总局电子发票服务平台的二维码交付页面自动下载电子发票PDF文件。
  处理二维码解码、Vue组件方法触发下载、network_requests捕获URL、提取发票元信息等全流程。
  当用户提供包含发票二维码的截图并需要下载PDF发票时使用此技能。
---

# 电子发票 PDF 下载 Agent

从国家税务总局电子发票服务平台的二维码交付页面**仅下载电子发票PDF文件**（不下载OFD和XML格式）。

> ⚠️ **本文档基于实战经验优化（2026-08）**：页面 JS 经过混淆，下载按钮由 Vue 组件方法 `openEwmjf` 触发，**拦截 `<a>.click()` 无法捕获 URL**。请严格按照下述"组件方法触发 + network_requests 捕获"流程操作。

## 触发时机

用户提供包含发票二维码的截图，并且需要下载电子发票 PDF 文件。

## 整体流程

### 第1步：解析二维码获取URL

用户会提供一张包含发票二维码的截图。需要执行以下操作：

1. 使用 `pyzbar` 库解码二维码
2. 如果直接解码失败，对图片做预处理（裁剪中心区域 + Otsu二值化）

**前置依赖安装：**

```bash
apt-get install -y libzbar0
pip install pyzbar opencv-python-headless Pillow requests --break-system-packages
```

**QR解码：** 使用 `scripts/decode_qrcode.py <图片路径>`，或参考 `scripts/decode_qrcode.py` 中的逻辑（中心裁剪 + Otsu 二值化）。

解码得到形如 `https://dppt.xxx.gov.cn:8443/v/2_{发票号码}_{时间戳}` 的URL。

### 第2步：浏览器打开页面

使用浏览器（Playwright）导航到解码出的URL。页面会自动重定向到 `qrcode` 页面，显示发票详情和三个下载按钮（`PDF下载`、`OFD下载`、`XML下载`）。**只需下载PDF**。

```
URL格式：https://dppt.sichuan.chinatax.gov.cn:8443/v/2_{发票号码}_{时间戳}
重定向后：https://dppt.sichuan.chinatax.gov.cn:8443/qrcode?cs=2_{发票号码}_{时间戳}&jrxt=EWMJF
```

> 各省平台域名可能不同（`dppt.{省}.chinatax.gov.cn`），以实际解码URL为准。

### 第3步：提取发票元信息与校验码（关键数据源）

从页面 Vue 组件中提取发票信息和下载所需的 `formData`。这一步的数据是后续触发下载的必要参数。

```javascript
// 在浏览器 evaluate 中执行：
var div = document.querySelector('.qrcode-box.g-layout-main__content-section');
var vm = div.__vue__;
var data = vm.$data || vm._data;
// 返回 data.formData，包含：
//   fphm: 发票号码
//   jym: 校验码（下载API必填）
//   kprq: 开票日期（yyyy-MM-dd HH:mm:ss）
//   jshj: 价税合计
//   gmfmc: 购买方名称 / gmfnsrsbh: 购买方税号
//   xsfmc: 销售方名称 / xsfnsrsbh: 销售方税号
//   fppz: 发票类型
```

同时从浏览器读取 Cookie（后续下载必需）：

```javascript
document.cookie
// 例：COOKIE_NAME_1_PLACEHOLDER=xxx; COOKIE_NAME_2_PLACEHOLDER=xxx
```

### 第4步：触发下载（关键！用组件方法而非click拦截）

**不要依赖拦截 `<a>.click()`**（实战验证返回空数组）。正确做法是：向上遍历 Vue 组件链，定位到包含 `openEwmjf`（或 `openEwmjfPDF`）方法的组件，然后**在该组件上下文直接调用此方法**，携带第3步的 `formData`。

```javascript
// 在浏览器 evaluate 中执行：
// 1) 找到目标组件（含 openEwmjf 方法）
var div = document.querySelector('.qrcode-box.g-layout-main__content-section');
var vm = div.__vue__;
var target = vm;
var depth = 0;
while (target && !(target.openEwmjf || target.openEwmjfPDF) && depth < 12) {
    target = target.$parent;
    depth++;
}
// 2) 从 formData 取参数
var f = vm.formData || vm.$data.formData;
// 3) 直接调用触发下载（Wjgs=PDF 仅下载PDF）
var r = target.openEwmjf({
    Wjgs: 'PDF',
    Jym: String(f.jym),
    Fphm: String(f.fphm),
    Kprq: String(f.kprq).replace(/[-: ]/g,'').slice(0,14), // yyyyMMddHHmmss
    Czsj: Date.now(),
    fileName: 'invoice_' + f.fphm + '.pdf',
    timeStampId: Date.now() + Math.floor(Math.random()*100)
});
```

> 若方法名在不同页面有变体（`openEwmjf` / `openEwmjfPDF`），遍历时两种都判断。触发成功后真实下载请求会发出。

### 第5步：从 network_requests 捕获真实下载URL

触发后立即读取浏览器网络请求，找到 `exportDzfpwjEwm`（PDF导出端点）的请求并提取完整URL。

```javascript
// 触发后调用浏览器 network_requests 工具，过滤出：
// /kpfw/fpjfzz/v1/exportDzfpwjEwm?Wjgs=PDF&Jym=...&Fphm=...&Kprq=...&Czsj=...&fileName=...&timeStampId=...
```

**下载URL格式：**

```
https://dppt.sichuan.chinatax.gov.cn:8443/kpfw/fpjfzz/v1/exportDzfpwjEwm?Wjgs=PDF&Jym={校验码}&Fphm={发票号码}&Kprq={yyyyMMddHHmmss}&Czsj={时间戳}&fileName={文件名}&timeStampId={时间戳ID}
```

> 页面 JS 主包（混淆）中可 grep 到端点系列：`exportDzfpwjEwm`(PDF)、`exportOfdwj`、`exportXmlwj`、`exportPdfwj`、`exportPrePdfwj` 等。若直接抓 URL 失败，可下载主JS包后 grep 这些端点做备选。

### 第6步：用Python下载PDF文件

拿到下载URL后，使用 `requests` 库下载PDF。**必须携带第3步读到的浏览器Cookie**（`verify=False`）。

使用 `scripts/download_pdf.py`：

```bash
python3 download_pdf.py "<下载URL>" {fphm} \
  --cookies "COOKIE_NAME_1_PLACEHOLDER=xxx; COOKIE_NAME_2_PLACEHOLDER=xxx" \
  --referer "https://dppt.sichuan.chinatax.gov.cn:8443/qrcode?cs=..." \
  --output-dir "OUTPUT_PATH_PLACEHOLDER"
```

下载后**必须校验**：文件头为 `%PDF-`、文件尾为 `%%EOF`。

### 第7步：按元信息重命名并归档到工作区

按发票元信息重命名，并保存到**工作区**文件夹（`OUTPUT_PATH_PLACEHOLDER`）：

```
电子发票_{fphm}_{购买方名称}_{金额}元.pdf
例：电子发票_INVOICE_NUMBER_PLACEHOLDER_BUYER_COMPANY_PLACEHOLDERAMOUNT_PLACEHOLDER元.pdf
```

## 关键注意事项（实战教训）

1. **❌ 不要用 `<a>.click()` 拦截**：该平台下载由 Vue 组件方法 `openEwmjf` 触发，拦截 click 会返回空数组。必须用"组件方法直接调用 + network_requests 捕获"。
2. **二维码解码**：直接解码可能失败，务必使用 Otsu 二值化预处理。
3. **Cookie 必需**：下载API需要登录态，必须携带 `document.cookie` 读到的非 httpOnly cookie（如 `COOKIE_NAME_1_PLACEHOLDER`、`COOKIE_NAME_2_PLACEHOLDER`）。
4. **仅下载PDF**：只下载PDF格式（`Wjgs=PDF`），不下载OFD和XML。
5. **文件验证**：PDF以 `%PDF-` 开头、`%%EOF` 结尾，下载后必须验证。
6. **不要用 WebFetch**：页面是SPA需JS渲染，必须用浏览器打开。
7. **输出路径**：统一保存到工作区 `OUTPUT_PATH_PLACEHOLDER/`。
8. **页面JS混淆**：直接读源码不可行，需下载主JS包后 grep 关键端点字符串。

## 完成输出格式

下载完成后，整理为表格：

| 格式 | 文件名 | 大小 | 状态 |
|:----:|--------|:----:|:----:|
| PDF | 电子发票_{fphm}_{购买方}_{金额}元.pdf | xxx KB | 有效 |

| 项目 | 内容 |
|:----|:----|
| 发票号码 | {fphm} |
| 发票类型 | {fppz} |
| 购买方 | {gmfmc} |
| 销售方 | {xsfmc} |
| 开票日期 | {kprq} |
| 价税合计 | ¥{jshj} |

## 参考

- `scripts/decode_qrcode.py` - 二维码解码脚本（中心裁剪 + Otsu二值化）
- `scripts/download_pdf.py` - PDF下载脚本（携带Cookie）
- `references/trigger_download.js` - Vue组件方法触发下载脚本
