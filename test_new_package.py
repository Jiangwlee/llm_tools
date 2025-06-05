#!/usr/bin/env python3
"""
测试新的 biddingcsg package

验证package结构和导入是否正常工作。
"""

import sys
import os

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_package_import():
    """测试package导入"""
    print("🧪 测试 biddingcsg package 导入...")
    
    try:
        import biddingcsg
        print(f"✅ Package导入成功")
        print(f"📦 Package版本: {biddingcsg.__version__}")
        print(f"📝 Package描述: {biddingcsg.__description__}")
        print(f"👨‍💻 作者: {biddingcsg.__author__}")
        
    except ImportError as e:
        print(f"❌ Package导入失败: {e}")
        return False
    
    return True

def test_module_structure():
    """测试模块结构"""
    print("\n🏗️ 测试模块结构...")
    
    modules_to_test = [
        'biddingcsg.core',
        'biddingcsg.models', 
        'biddingcsg.services',
        'biddingcsg.ui',
        'biddingcsg.utils',
        'biddingcsg.config'
    ]
    
    success_count = 0
    
    for module_name in modules_to_test:
        try:
            __import__(module_name)
            print(f"✅ {module_name} - 导入成功")
            success_count += 1
        except ImportError as e:
            print(f"❌ {module_name} - 导入失败: {e}")
    
    print(f"\n📊 模块导入结果: {success_count}/{len(modules_to_test)} 成功")
    return success_count == len(modules_to_test)

def test_package_info():
    """测试package信息"""
    print("\n📋 Package信息:")
    
    try:
        import biddingcsg
        
        # 显示可用的公共接口
        print(f"🔧 可用组件: {biddingcsg.__all__}")
        
        # 检查package位置
        print(f"📍 Package位置: {biddingcsg.__file__}")
        
        # 检查模块文档
        if biddingcsg.__doc__:
            print(f"📚 Package文档:")
            print(biddingcsg.__doc__[:200] + "..." if len(biddingcsg.__doc__) > 200 else biddingcsg.__doc__)
        
        return True
        
    except Exception as e:
        print(f"❌ 获取package信息失败: {e}")
        return False

def test_directory_structure():
    """检查目录结构"""
    print("\n📁 检查目录结构...")
    
    base_path = "src/biddingcsg"
    expected_dirs = [
        "core",
        "models", 
        "services",
        "ui",
        "utils",
        "config"
    ]
    
    expected_files = [
        "__init__.py",
        "README.md",
        "ROADMAP.md"
    ]
    
    success = True
    
    # 检查目录
    for dir_name in expected_dirs:
        dir_path = os.path.join(base_path, dir_name)
        if os.path.isdir(dir_path):
            print(f"✅ 目录存在: {dir_name}/")
            
            # 检查__init__.py
            init_file = os.path.join(dir_path, "__init__.py")
            if os.path.isfile(init_file):
                print(f"   ✅ {dir_name}/__init__.py 存在")
            else:
                print(f"   ❌ {dir_name}/__init__.py 缺失")
                success = False
        else:
            print(f"❌ 目录缺失: {dir_name}/")
            success = False
    
    # 检查文件
    for file_name in expected_files:
        file_path = os.path.join(base_path, file_name)
        if os.path.isfile(file_path):
            print(f"✅ 文件存在: {file_name}")
        else:
            print(f"❌ 文件缺失: {file_name}")
            success = False
    
    return success

def main():
    """主测试函数"""
    print("🚀 BiddingCSG v2.0 Package 测试")
    print("=" * 60)
    
    tests = [
        ("Package导入测试", test_package_import),
        ("模块结构测试", test_module_structure), 
        ("Package信息测试", test_package_info),
        ("目录结构测试", test_directory_structure)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n📝 开始: {test_name}")
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} 执行异常: {e}")
            results.append((test_name, False))
        
        print("-" * 40)
    
    # 总结
    print("\n📊 测试结果总结:")
    print("=" * 60)
    
    passed = 0
    for test_name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{status} - {test_name}")
        if result:
            passed += 1
    
    total = len(results)
    print(f"\n🎯 总体结果: {passed}/{total} 测试通过")
    
    if passed == total:
        print("🎉 所有测试通过！Package结构创建成功。")
        print("\n📋 下一步建议:")
        print("1. 开始实现 Phase 1 的基础工具类")
        print("2. 创建配置管理系统")
        print("3. 实现数据模型")
    else:
        print("⚠️ 部分测试失败，请检查package结构。")
    
    return passed == total

if __name__ == "__main__":
    main() 