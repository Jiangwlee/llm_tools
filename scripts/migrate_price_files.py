#!/usr/bin/env python3
"""
价格文件迁移脚本

将旧位置的价格文件迁移到新的 bidding_data/price 目录结构
"""

import os
import sys
import shutil
from pathlib import Path
from datetime import datetime

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.biddingcsg.config.paths import BiddingPaths, FilePatterns

def migrate_price_files(output_directory: str, dry_run: bool = True):
    """
    迁移价格文件到新目录结构
    
    Args:
        output_directory: 输出目录路径
        dry_run: 是否为模拟运行（不实际移动文件）
    """
    output_path = Path(output_directory)
    if not output_path.exists():
        print(f"❌ 输出目录不存在: {output_path}")
        return False
    
    # 使用全局路径配置
    new_price_dir = BiddingPaths.get_price_dir(output_directory)
    
    # 扫描旧位置的价格文件
    old_price_files = list(output_path.glob(FilePatterns.PRICE_EXTRACTION_GLOB))
    
    if not old_price_files:
        print("✅ 未发现需要迁移的价格文件")
        return True
    
    print(f"🔍 发现 {len(old_price_files)} 个价格文件需要迁移")
    
    # 创建新目录
    if not dry_run:
        new_price_dir.mkdir(parents=True, exist_ok=True)
        print(f"📁 创建目录: {new_price_dir}")
    else:
        print(f"📁 [模拟] 将创建目录: {new_price_dir}")
    
    # 迁移文件
    moved_count = 0
    for old_file in old_price_files:
        new_file = new_price_dir / old_file.name
        
        try:
            if not dry_run:
                shutil.move(str(old_file), str(new_file))
                print(f"✅ 移动: {old_file.name} -> {new_file}")
            else:
                print(f"📄 [模拟] 将移动: {old_file.name} -> {new_file.relative_to(output_path)}")
            moved_count += 1
        except Exception as e:
            print(f"❌ 移动失败 {old_file.name}: {e}")
    
    if not dry_run:
        print(f"🎉 迁移完成！成功移动 {moved_count} 个文件")
    else:
        print(f"📋 模拟完成！将移动 {moved_count} 个文件")
        print("💡 运行时添加 --execute 参数来实际执行迁移")
    
    return True

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="迁移价格文件到新目录结构")
    parser.add_argument("output_directory", help="输出目录路径")
    parser.add_argument("--execute", action="store_true", help="实际执行迁移（默认为模拟运行）")
    
    args = parser.parse_args()
    
    print("🔄 价格文件迁移工具")
    print("=" * 50)
    print(f"📁 输出目录: {args.output_directory}")
    print(f"🔧 模式: {'实际执行' if args.execute else '模拟运行'}")
    print()
    
    success = migrate_price_files(args.output_directory, dry_run=not args.execute)
    
    if success:
        print("\n✅ 迁移任务完成")
    else:
        print("\n❌ 迁移任务失败")
        exit(1)

if __name__ == "__main__":
    main() 