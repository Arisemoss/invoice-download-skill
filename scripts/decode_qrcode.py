#!/usr/bin/env python3
"""
发票二维码解码脚本（支持多省份）
从用户提供的截图/图片中解码发票交付页面的二维码URL，并自动识别省份。

用法：
    python3 decode_qrcode.py <image_path> [--province <province_code>]

支持省份：
    sichuan（四川）、guangdong（广东）、zhejiang（浙江）、
    beijing（北京）、shanghai（上海）、jiangsu（江苏）、shandong（山东）

前置依赖：
    apt-get install -y libzbar0
    pip install pyzbar opencv-python-headless Pillow requests --break-system-packages
"""

import sys
import os
import json
import re
import cv2
import numpy as np
from pyzbar.pyzbar import decode
from PIL import Image


def load_province_config():
    """加载省份配置文件"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(script_dir, "../references/province_config.json")
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        # 返回默认配置
        return {
            "provinces": {
                "sichuan": {
                    "name": "四川",
                    "domain": "dppt.sichuan.chinatax.gov.cn",
                    "port": 8443,
                    "url_pattern": "https://dppt.sichuan.chinatax.gov.cn:8443/v/2_{fphm}_{timestamp}",
                    "notes": "四川税务电子发票服务平台"
                }
            },
            "default_province": "sichuan"
        }


def identify_province(url):
    """从URL中识别省份"""
    config = load_province_config()
    
    # 提取域名部分
    domain_match = re.search(r'https?://([^/:]+)', url)
    if not domain_match:
        return config["default_province"], config["provinces"][config["default_province"]]
    
    domain = domain_match.group(1)
    
    # 遍历省份配置，匹配域名
    for province_code, province_info in config["provinces"].items():
        if province_info["domain"] in domain:
            return province_code, province_info
    
    # 如果没有匹配，尝试从域名提取省份
    province_match = re.search(r'dppt\.([^.]+)\.chinatax\.gov\.cn', domain)
    if province_match:
        province_name = province_match.group(1)
        for province_code, province_info in config["provinces"].items():
            if province_name in province_info["domain"]:
                return province_code, province_info
    
    return config["default_province"], config["provinces"][config["default_province"]]


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


def extract_invoice_info(url):
    """从URL中提取发票信息"""
    # 尝试提取发票号码和时间戳
    # URL格式：https://dppt.xxx.chinatax.gov.cn:8443/v/2_{发票号码}_{时间戳}
    pattern = r'/v/2_(\d+)_(\d+)'
    match = re.search(pattern, url)
    
    if match:
        fphm = match.group(1)
        timestamp = match.group(2)
        return {
            "fphm": fphm,
            "timestamp": timestamp,
            "full_url": url
        }
    
    return {"full_url": url}


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python3 decode_qrcode.py <image_path> [--province <province_code>]")
        print("支持省份: sichuan, guangdong, zhejiang, beijing, shanghai, jiangsu, shandong")
        sys.exit(1)

    path = sys.argv[1]
    province_code = None
    
    # 解析命令行参数
    if len(sys.argv) > 2 and sys.argv[2] == "--province":
        if len(sys.argv) > 3:
            province_code = sys.argv[3]
    
    try:
        url = decode_qrcode(path)
        print(f"解码URL: {url}")
        
        # 识别省份
        if province_code:
            config = load_province_config()
            if province_code in config["provinces"]:
                province_info = config["provinces"][province_code]
                print(f"省份: {province_info['name']} ({province_code})")
            else:
                print(f"未知省份代码: {province_code}")
        else:
            province_code, province_info = identify_province(url)
            print(f"识别省份: {province_info['name']} ({province_code})")
        
        # 提取发票信息
        invoice_info = extract_invoice_info(url)
        if "fphm" in invoice_info:
            print(f"发票号码: {invoice_info['fphm']}")
            print(f"时间戳: {invoice_info['timestamp']}")
        
        # 输出JSON格式结果
        result = {
            "url": url,
            "province": province_code,
            "province_name": province_info["name"],
            "invoice_info": invoice_info
        }
        print(f"\nJSON结果: {json.dumps(result, ensure_ascii=False, indent=2)}")
        
    except Exception as e:
        print(f"错误: {e}")
        sys.exit(1)