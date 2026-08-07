// 电子发票下载触发脚本（实战验证版）
// 页面 JS 混淆，下载由 Vue 组件方法 openEwmjf 触发。
// ⚠️ 拦截 <a>.click() 无效（返回空数组），必须用本方法在组件上下文直接调用。
// 在浏览器 evaluate 中执行。执行后需配合 network_requests 捕获真实下载URL。

(function() {
    // 1) 找到目标组件（含 openEwmjf / openEwmjfPDF 方法），向上遍历组件链
    var div = document.querySelector('.qrcode-box.g-layout-main__content-section');
    if (!div) {
        // 备选选择器
        div = document.querySelector('.qrcode-box') || document.body;
    }
    var vm = div.__vue__ || div.__vueParentComponent?.proxy;
    if (!vm) { console.error('[Invoice] 未找到Vue组件'); return null; }

    var target = vm;
    var depth = 0;
    var methodName = null;
    while (target && depth < 12) {
        if (typeof target.openEwmjf === 'function') { methodName = 'openEwmjf'; break; }
        if (typeof target.openEwmjfPDF === 'function') { methodName = 'openEwmjfPDF'; break; }
        target = target.$parent;
        depth++;
    }
    if (!target || !methodName) {
        console.error('[Invoice] 未找到 openEwmjf/openEwmjfPDF 方法');
        return null;
    }

    // 2) 从 formData 取参数（fphm/jym/kprq 等）
    var f = vm.formData || vm.$data?.formData || vm._data?.formData;
    if (!f) { console.error('[Invoice] 未找到 formData'); return null; }

    var params = {
        Wjgs: 'PDF',                      // 仅下载PDF
        Jym: String(f.jym),               // 校验码（下载API必填）
        Fphm: String(f.fphm),             // 发票号码
        Kprq: String(f.kprq).replace(/[-: ]/g, '').slice(0, 14), // yyyyMMddHHmmss
        Czsj: Date.now(),
        fileName: 'invoice_' + f.fphm + '.pdf',
        timeStampId: Date.now() + Math.floor(Math.random() * 100)
    };

    // 3) 在组件上下文调用，触发真实下载请求
    var r = target[methodName](params);

    console.log('[Invoice] 触发下载:', methodName, JSON.stringify(params));
    // 返回参数供外部记录
    return { method: methodName, params: params, returnValue: r };
})();

// 触发后，立即用浏览器 network_requests 工具过滤出：
// /kpfw/fpjfzz/v1/exportDzfpwjEwm?Wjgs=PDF&Jym=...&Fphm=...&Kprq=...&Czsj=...&fileName=...&timeStampId=...
// 拿到完整URL后，用 download_pdf.py 携带Cookie下载。
