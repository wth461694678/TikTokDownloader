#!/usr/bin/env python3
"""
Simple Python script that prints input parameters line by line.
"""

import sys
import argparse
import requests
import json

def send_markdown_message(key, content):
    headers = {
        'Content-Type': 'application/json; charset=utf-8'
    }
    params = {'key': key}
    data = {"msgtype": "markdown", "markdown": {"content": content}}
    
    # 确保使用UTF-8编码进行JSON序列化
    json_data = json.dumps(data, ensure_ascii=False, indent=None, separators=(',', ':'))
    
    response = requests.post(
        'https://qyapi.weixin.qq.com/cgi-bin/webhook/send', 
        params=params, 
        headers=headers, 
        data=json_data.encode('utf-8')
    )
    return response


def main():
    """Main function to process and print input parameters."""
    parser = argparse.ArgumentParser(description='Print input parameters line by line')
    
    # 添加两个必填参数
    parser.add_argument('param1', type=str, help='First required string parameter')
    parser.add_argument('param2', type=str, help='Second required string parameter')
    
    # 添加一个可选参数
    parser.add_argument('--param3', type=str, default='', help='Optional third string parameter')
    
    args = parser.parse_args()
    
    # 逐行打印参数
    print(f"Parameter 1: {args.param1}")
    print(f"Parameter 2: {args.param2}")
    if args.param3:
        print(f"Parameter 3: {args.param3}")
    else:
        print("Parameter 3: (not provided)")
    
    # 准备发送的内容
    content_lines = [
        f"Parameter 1: {args.param1}",
        f"Parameter 2: {args.param2}"
    ]
    
    if args.param3:
        content_lines.append(f"Parameter 3: {args.param3}")
    else:
        content_lines.append("Parameter 3: (not provided)")
    
    content = "\n".join(content_lines)
    
    # 调用send_markdown_message
    key = "c6b2ff61-ec4d-49bc-a41b-80fa935f7112"
    try:
        response = send_markdown_message(key, content)
        print(f"Message sent successfully. Response status: {response.status_code}")
    except Exception as e:
        print(f"Error sending message: {e}")


if __name__ == "__main__":
    main()