// 电子发票下载拦截脚本
// 在浏览器控制台执行，拦截所有 HTMLAnchorElement 的 click 事件来捕获下载URL。
// 必须在点击"PDF下载"按钮之前运行此脚本。

(function() {
    // 拦截 HTMLAnchorElement.prototype.click 捕获下载URL
    var origClick = HTMLAnchorElement.prototype.click;

    // 存储被点击的链接信息
    window.__clickedUrls = [];

    HTMLAnchorElement.prototype.click = function() {
        window.__clickedUrls.push({
            href: this.href,
            download: this.download,
            time: Date.now()
        });
        console.log('[InvoiceCapture] 捕获到点击:', this.href);
        return origClick.apply(this, arguments);
    };

    console.log('[InvoiceCapture] 拦截脚本已注入，等待点击下载按钮...');
})();

// 在点击"PDF下载"按钮后，通过以下命令获取捕获的URL：
// window.__clickedUrls