#!/usr/bin/env python3
"""
测试downloads目录功能
"""

import os
import csv
from pathlib import Path
import json

def test_downloads_directory():
    """测试downloads目录的创建和CSV文件写入"""
    
    # 确保downloads目录存在
    downloads_dir = Path("./downloads")
    downloads_dir.mkdir(exist_ok=True)
    
    print(f"✅ Downloads目录路径: {downloads_dir.absolute()}")
    
    # 创建测试CSV文件
    test_csv_path = downloads_dir / "test_data.csv"
    
    # 写入测试数据
    test_data = [
        ["作品ID", "作者", "标题", "发布时间", "点赞数"],
        ["7123456789", "测试用户1", "这是一个测试视频", "2024-01-01 10:00:00", "1000"],
        ["7123456790", "测试用户2", "另一个测试视频", "2024-01-01 11:00:00", "2000"],
        ["7123456791", "测试用户3", "第三个测试视频", "2024-01-01 12:00:00", "3000"],
        ["7123456792", "测试用户4", "第四个测试视频", "2024-01-01 13:00:00", "4000"],
        ["7123456793", "测试用户5", "第五个测试视频", "2024-01-01 14:00:00", "5000"],
    ]
    
    with open(test_csv_path, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        writer.writerows(test_data)
    
    print(f"✅ 创建测试CSV文件: {test_csv_path}")
    
    # 测试读取CSV文件
    def read_csv_first_rows(csv_path: str, rows: int = 5) -> str:
        """读取CSV文件的前几行并格式化为Markdown表格"""
        try:
            with open(csv_path, 'r', encoding='utf-8-sig') as f:
                reader = csv.reader(f)
                data = []
                for i, row in enumerate(reader):
                    if i >= rows:
                        break
                    data.append(row)
            
            if not data:
                return "CSV文件为空"
            
            # 格式化为Markdown表格
            if len(data) == 1:
                return f"CSV只有标题行: {', '.join(data[0])}"
            
            markdown = "CSV文件前5行:\n\n"
            
            # 表头
            if data:
                markdown += "| " + " | ".join(data[0]) + " |\n"
                markdown += "|" + "---|" * len(data[0]) + "\n"
            
            # 数据行
            for row in data[1:]:
                # 确保行的列数与表头一致
                while len(row) < len(data[0]):
                    row.append("")
                markdown += "| " + " | ".join(row[:len(data[0])]) + " |\n"
            
            return markdown
            
        except Exception as e:
            return f"读取CSV文件失败: {e}"
    
    # 测试读取功能
    csv_content = read_csv_first_rows(test_csv_path)
    print("✅ CSV内容读取测试:")
    print(csv_content)
    
    # 测试文件查找逻辑
    import glob
    csv_files = glob.glob(str(downloads_dir / "*.csv"))
    print(f"✅ 找到的CSV文件: {csv_files}")
    
    return True


def test_path_parameters():
    """测试路径参数"""
    from pathlib import Path
    
    # 模拟PROJECT_ROOT
    PROJECT_ROOT = Path.cwd()
    downloads_dir = str(Path(PROJECT_ROOT) / "downloads")
    
    print(f"✅ 项目根目录: {PROJECT_ROOT}")
    print(f"✅ Downloads目录: {downloads_dir}")
    print(f"✅ Downloads目录存在: {Path(downloads_dir).exists()}")
    
    return True


if __name__ == "__main__":
    print("=" * 60)
    print("测试downloads目录功能")
    print("=" * 60)
    
    try:
        # 测试downloads目录
        test_downloads_directory()
        print()
        
        # 测试路径参数
        test_path_parameters()
        print()
        
        print("✅ 所有测试通过!")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()