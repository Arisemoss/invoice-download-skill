#!/usr/bin/env python3
"""
发票二维码解码脚本
从用户提供的截图/图片中解码发票交付页面的二维码URL。

用法：
    python3 decode_qrcode.py <image_path>

前置依赖：
    apt-get install -y libzbar0
    pip install pyzbar opencv-python-headless Pillow --break-system-packages
"""

import sys
import cv2
import numpy as np
from pyzbar.pyzbar import decode
from PIL import Image


def decode_qrcode(image_path):
    """
    从图片路径解码二维码，返回URL字符串。
    先用中心区域直接解码，失败后用Otsu二值化再试。
    """
    img = cv2.imread(image_path)
    if img is None:
        raise ValueError(f"无法读取图片: {image_path}")

    h, w = img.shape[:2]

    # 裁剪中心区域（二维码通常在中间）
    cx, cy = w // 2, h // 2
    crop_size = min(w, h) // 2
    center = img[cy - crop_size:cy + crop_size, cx - crop_size:cx + crop_size]

    # 尝试直接解码
    rgb_center = cv2.cvtColor(center, cv2.COLOR_BGR2RGB)
    results = decode(Image.fromarray(rgb_center))

    # 若失败，执行Otsu二值化
    if not results:
        gray = cv2.cvtColor(center, cv2.COLOR_BGR2GRAY)
        _, otsu = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        results = decode(Image.fromarray(otsu))

    if not results:
        raise ValueError("无法解码二维码，请尝试提供更清晰的图片")

    # 返回URL
    return results[0].data.decode('utf-8')


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python3 decode_qrcode.py <image_path>")
        sys.exit(1)

    path = sys.argv[1]
    try:
        url = decode_qrcode(path)
        print(f"解码URL: {url}")
    except Exception as e:
        print(f"错误: {e}")
        sys.exit(1)