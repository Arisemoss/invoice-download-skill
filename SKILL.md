---
name: invoice-download
description: >
  从国家税务总局电子发票服务平台的二维码交付页面自动下载电子发票PDF文件。
  处理二维码解码、浏览器拦截下载链接、提取发票元信息等全流程。
  当用户提供包含发票二维码的截图并需要下载PDF发票时使用此技能。
---

# 电子发票 PDF 下载 Agent

从国家税务总局电子发票服务平台的二维码交付页面**仅下载电子发票PDF文件**（不下载OFD和XML格式）。

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

**QR解码代码：**

使用 `scripts/decode_qrcode.py` 脚本或手动执行以下Python代码：

```python
import cv2
import numpy as np
from pyzbar.pyzbar import decode
from PIL import Image

img = cv2.imread('图片路径')
h, w = img.shape[:2]

# 裁剪中心区域（二维码通常在中间）
cx, cy = w // 2, h // 2
crop_size = min(w, h) // 2
center = img[cy - crop_size:cy + crop_size, cx - crop_size:cx + crop_size]

# 尝试直接解码
results = decode(Image.fromarray(cv2.cvtColor(center, cv2.COLOR_BGR2RGB)))

# 若失败，执行Otsu二值化
if not results:
    gray = cv2.cvtColor(center, cv2.COLOR_BGR2GRAY)
    _, otsu = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    results = decode(Image.fromarray(otsu))

if not results:
    raise ValueError("无法解码二维码，请尝试提供更清晰的图片")

url = results[0].data.decode('utf-8')
# 得到形如 https://dppt.xxx.gov.cn:8443/v/2_xxx 的URL
print(f"解码URL: {url}")
```

### 第2步：浏览器打开页面

使用浏览器导航到解码出的URL。页面会自动重定向到 `qrcode` 页面，显示发票详情和下载按钮。

```
URL格式：https://dppt.sichuan.chinatax.gov.cn:8443/v/2_{发票号码}_{时间戳}
重定向后：https://dppt.sichuan.chinatax.gov.cn:8443/qrcode?cs=2_{发票号码}_{时间戳}&jrxt=EWMJF
```

页面加载后显示三个下载按钮：`PDF下载`、`OFD下载`、`XML下载`。**只需点击PDF下载**。

### 第3步：拦截下载链接（关键！）

点击下载按钮不会直接触发浏览器下载，而是通过JS动态创建 `<a>` 标签触发。需要在**点击之前**注入拦截脚本：

```javascript
// 拦截 HTMLAnchorElement.prototype.click 捕获下载URL
var origClick = HTMLAnchorElement.prototype.click;
var clickedUrls = [];
HTMLAnchorElement.prototype.click = function() {
    clickedUrls.push({href: this.href, download: this.download, time: Date.now()});
    return origClick.apply(this, arguments);
};
window.__clickedUrls = clickedUrls;
```

### 第4步：点击PDF下载按钮并捕获URL

在注入拦截后，点击"PDF下载"按钮，然后读取 `window.__clickedUrls` 获取下载URL。

**下载URL格式：**

```
https://dppt.sichuan.chinatax.gov.cn:8443/kpfw/fpjfzz/v1/exportDzfpwjEwm?Wjgs=PDF&Jym={校验码}&Fphm={发票号码}&Kprq={开票日期}&Czsj={时间戳}&fileName=&timeStampId={时间戳ID}
```

参数说明：
- `Wjgs`：文件格式，固定为 PDF
- `Jym`：校验码
- `Fphm`：发票号码
- `Kprq`：开票日期（格式 `yyyyMMddHHmmss`）
- `Czsj` 和 `timeStampId`：从拦截到的URL中获取即可

### 第5步：用Python下载PDF文件

拿到下载URL后，使用 `requests` 库下载PDF文件。**必须携带浏览器Cookie**。

使用 `scripts/download_pdf.py` 脚本或参考以下代码：

```python
import requests
import urllib3
urllib3.disable_warnings()

cookies = {
    "_preview_auth": "从浏览器获取",
    "COOKIE_NAME_1_PLACEHOLDER": "从浏览器获取",
    "COOKIE_NAME_2_PLACEHOLDER": "从浏览器获取"
}

headers = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "*/*",
    "Referer": "https://dppt.sichuan.chinatax.gov.cn:8443/qrcode?cs=..."
}

# 仅下载PDF格式
resp = requests.get(captured_url, cookies=cookies, headers=headers, verify=False, timeout=30)

if resp.status_code == 200 and len(resp.content) > 500:
    filepath = f"/workspace/发票_{fphm}.pdf"
    with open(filepath, "wb") as f:
        f.write(resp.content)
    print(f"PDF下载成功: {filepath} ({len(resp.content)} bytes)")
else:
    print(f"PDF下载失败: HTTP {resp.status_code}, 大小 {len(resp.content)} bytes")
```

### 第6步：提取发票元信息

从页面Vue组件中提取发票信息：

```javascript
var div = document.querySelector('.qrcode-box.g-layout-main__content-section');
var vm = div.__vue__;
var data = vm.$data || vm._data;
// data.formData 包含：
//   fphm: 发票号码
//   jym: 校验码
//   kprq: 开票日期
//   jshj: 价税合计
//   gmfnsrsbh: 购买方税号
//   gmfmc: 购买方名称
//   xsfnsrsbh: 销售方税号
//   xsfmc: 销售方名称
//   fppz: 发票类型
```

## 关键注意事项

1. **二维码解码**：直接解码可能失败，务必使用 Otsu 二值化预处理
2. **拦截时机**：必须在点击按钮**之前**注入 `HTMLAnchorElement.prototype.click` 拦截
3. **Cookie必需**：下载API需要登录态，必须携带浏览器的Cookie
4. **仅下载PDF**：只下载PDF格式，无需下载OFD和XML，避免不必要的请求
5. **文件验证**：PDF文件以 `%PDF-` 开头，下载后必须验证
6. **不要用WebFetch**：页面是SPA需要JS渲染，必须用浏览器打开

## 完成输出格式

下载完成后，整理为表格：

| 格式 | 文件名 | 大小 | 状态 |
|:----:|--------|:----:|:----:|
| PDF | 发票_{fphm}.pdf | xxx KB | 有效 |

| 项目 | 内容 |
|:----|:----|
| 发票号码 | {fphm} |
| 发票类型 | {fppz} |
| 购买方 | {gmfmc} |
| 销售方 | {xsfmc} |
| 开票日期 | {kprq} |
| 价税合计 | ¥{jshj} |

## 参考

- `scripts/decode_qrcode.py` - 二维码解码脚本
- `scripts/download_pdf.py` - PDF下载脚本
- `references/intercept.js` - 浏览器下载链接拦截脚本