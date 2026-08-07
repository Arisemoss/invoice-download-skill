#!/usr/bin/env python3
"""
电子发票PDF下载脚本
根据拦截到的下载URL，携带Cookie下载PDF文件。

用法：
    python3 download_pdf.py <captured_url> <fphm> --cookies "COOKIE_NAME_1_PLACEHOLDER=xxx; COOKIE_NAME_2_PLACEHOLDER=xxx" --output-dir "工作区路径"
"""

import sys
import argparse
import requests
import urllib3
import os

urllib3.disable_warnings()


def parse_cookies(cookie_str):
    """将 'key1=val1; key2=val2' 格式的Cookie字符串转为字典"""
    cookies = {}
    if cookie_str:
        for pair in cookie_str.split(';'):
            if '=' in pair:
                k, v = pair.strip().split('=', 1)
                cookies[k] = v
    return cookies


def download_pdf(url, fphm, cookie_dict, referer=None, output_dir="/workspace"):
    """下载PDF文件到指定目录"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "*/*",
        "Accept-Encoding": "identity",
    }
    if referer:
        headers["Referer"] = referer

    print(f"请求下载URL: {url[:200]}...")
    resp = requests.get(url, cookies=cookie_dict, headers=headers,
                        verify=False, timeout=30)

    if resp.status_code == 200 and len(resp.content) > 500:
        filepath = os.path.join(output_dir, f"发票_{fphm}.pdf")
        with open(filepath, "wb") as f:
            f.write(resp.content)
        size_kb = len(resp.content) / 1024
        print(f"PDF下载成功: {filepath} ({size_kb:.1f} KB)")
        return filepath
    else:
        print(f"PDF下载失败: HTTP {resp.status_code}, 大小 {len(resp.content)} bytes")
        return None


def main():
    parser = argparse.ArgumentParser(description='电子发票PDF下载')
    parser.add_argument('url', help='拦截到的下载URL')
    parser.add_argument('fphm', help='发票号码')
    parser.add_argument('--cookies', help='Cookie字符串，格式: "k=v; k2=v2"')
    parser.add_argument('--referer', help='Referer URL')
    parser.add_argument('--output-dir', default='OUTPUT_PATH_PLACEHOLDER', help='保存目录（默认工作区）')

    args = parser.parse_args()

    cookies = parse_cookies(args.cookies)
    if not cookies:
        print("警告: 未提供Cookie，下载可能失败！")

    result = download_pdf(args.url, args.fphm, cookies,
                          referer=args.referer, output_dir=args.output_dir)

    if result:
        print(f"\n✅ 下载完成: {result}")
        sys.exit(0)
    else:
        print("\n❌ 下载失败")
        sys.exit(1)


if __name__ == "__main__":
    main()