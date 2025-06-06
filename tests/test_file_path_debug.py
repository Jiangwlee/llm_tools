"""调试价格文件路径问题的测试脚本"""

import json
import tempfile
from pathlib import Path
from datetime import datetime
import sys

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def test_file_generation_pattern():
    """测试文件生成模式"""
    print("🔍 测试文件生成模式...")
    
    # 模拟价格提取文件生成
    keyword = "测试关键词"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # 这是价格提取功能使用的文件名格式
    filename = f"price_extraction_{keyword}_{timestamp}.json"
    print(f"📄 生成的文件名: {filename}")
    
    # 检查是否符合扫描模式
    import fnmatch
    pattern = "price_extraction_*.json"
    matches = fnmatch.fnmatch(filename, pattern)
    print(f"🎯 是否匹配扫描模式 '{pattern}': {matches}")
    
    return filename, matches

def test_directory_creation_and_scanning():
    """测试目录创建和扫描"""
    print("\n🗂️ 测试目录创建和扫描...")
    
    # 创建临时目录
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        print(f"📁 临时目录: {temp_path}")
        
        # 创建测试文件
        test_files = [
            "price_extraction_keyword1_20240101_120000.json",
            "price_extraction_keyword2_20240102_130000.json", 
            "other_file.json",
            "data.txt"
        ]
        
        for filename in test_files:
            file_path = temp_path / filename
            test_data = {
                "extraction_time": datetime.now().isoformat(),
                "total_files": 10,
                "successful_extractions": 8,
                "results": []
            }
            
            if filename.endswith('.json'):
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(test_data, f, ensure_ascii=False, indent=2)
            else:
                file_path.write_text("test content")
            
            print(f"  ✅ 创建文件: {filename}")
        
        # 测试扫描
        print("\n🔍 测试扫描结果:")
        
        # 所有文件
        all_files = list(temp_path.glob("*"))
        print(f"📊 总文件数: {len(all_files)}")
        
        # JSON文件
        json_files = list(temp_path.glob("*.json"))
        print(f"📊 JSON文件数: {len(json_files)}")
        for f in json_files:
            print(f"  - {f.name}")
        
        # 价格文件
        price_files = list(temp_path.glob("price_extraction_*.json"))
        print(f"📊 价格文件数: {len(price_files)}")
        for f in price_files:
            print(f"  - {f.name}")
        
        return len(price_files) == 2

def test_crawler_config_scanning():
    """测试CrawlerConfig的扫描功能"""
    print("\n🔧 测试CrawlerConfig扫描功能...")
    
    try:
        from src.biddingcsg.ui.pages.crawler_config import CrawlerConfigPage
        
        # 创建配置页面实例
        config_page = CrawlerConfigPage()
        
        # 创建临时目录和测试文件
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # 创建测试价格文件
            test_data = {
                "extraction_time": datetime.now().isoformat(),
                "total_files": 15,
                "successful_extractions": 12,
                "results": [
                    {
                        "file_name": "test1.html",
                        "title": "测试标题1",
                        "extracted_info": "测试价格信息"
                    }
                ]
            }
            
            test_file = temp_path / "price_extraction_测试_20240101_120000.json"
            with open(test_file, 'w', encoding='utf-8') as f:
                json.dump(test_data, f, ensure_ascii=False, indent=2)
            
            print(f"✅ 创建测试文件: {test_file.name}")
            
            # 测试扫描
            print("🔍 开始扫描...")
            files_info = config_page._scan_price_files(str(temp_path))
            
            print(f"📊 扫描结果: 找到 {len(files_info)} 个价格文件")
            
            if files_info:
                for file_info in files_info:
                    print(f"  📄 文件: {file_info['name']}")
                    print(f"     关键词: {file_info['keyword']}")
                    print(f"     成功率: {file_info.get('success_rate', 0):.1f}%")
                    print(f"     处理文件数: {file_info.get('total_files', 0)}")
            
            return len(files_info) > 0
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def simulate_real_extraction():
    """模拟真实的价格提取过程"""
    print("\n🚀 模拟真实价格提取过程...")
    
    # 创建临时输出目录
    with tempfile.TemporaryDirectory() as temp_dir:
        output_dir = Path(temp_dir)
        html_dir = output_dir / "raw_html"
        html_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"📁 输出目录: {output_dir}")
        print(f"📁 HTML目录: {html_dir}")
        
        # 创建模拟HTML文件
        html_content = """
        <html>
        <head><title>公示公告 - 测试项目</title></head>
        <body>
            <h1>公示公告</h1>
            <div class="Content">
                <p>包含测试关键词的内容</p>
                <p>>投标报价< 100万元</p>
            </div>
        </body>
        </html>
        """
        
        html_file = html_dir / "公示公告_测试项目_20240101.html"
        html_file.write_text(html_content, encoding='utf-8')
        print(f"✅ 创建HTML文件: {html_file.name}")
        
        # 模拟生成价格提取结果
        keyword = "测试关键词"
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = output_dir / f"price_extraction_{keyword}_{timestamp}.json"
        
        extraction_result = {
            "extraction_time": datetime.now().isoformat(),
            "total_files": 1,
            "successful_extractions": 1,
            "results": [
                {
                    "file_path": str(html_file),
                    "file_name": html_file.name,
                    "title": "公示公告 - 测试项目",
                    "success": True,
                    "extracted_info": "中标价格：100万元"
                }
            ]
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(extraction_result, f, ensure_ascii=False, indent=2)
        
        print(f"✅ 生成价格提取结果: {output_file.name}")
        
        # 验证文件是否能被扫描到
        try:
            from src.biddingcsg.ui.pages.crawler_config import CrawlerConfigPage
            config_page = CrawlerConfigPage()
            
            files_info = config_page._scan_price_files(str(output_dir))
            print(f"🔍 扫描结果: 找到 {len(files_info)} 个价格文件")
            
            if files_info:
                file_info = files_info[0]
                print(f"  📄 文件名: {file_info['name']}")
                print(f"  🎯 关键词: {file_info['keyword']}")
                print(f"  📊 处理文件数: {file_info['total_files']}")
                print(f"  ✅ 成功提取: {file_info['successful_extractions']}")
                print(f"  📈 成功率: {file_info['success_rate']:.1f}%")
                return True
            else:
                print("❌ 未能扫描到生成的价格文件")
                return False
                
        except Exception as e:
            print(f"❌ 扫描测试失败: {e}")
            return False

def main():
    """主测试函数"""
    print("🧪 开始调试价格文件路径问题...\n")
    
    results = []
    
    # 测试1：文件生成模式
    filename, matches = test_file_generation_pattern()
    results.append(("文件生成模式", matches))
    
    # 测试2：目录扫描
    scan_result = test_directory_creation_and_scanning()
    results.append(("目录扫描", scan_result))
    
    # 测试3：CrawlerConfig扫描
    config_scan_result = test_crawler_config_scanning()
    results.append(("CrawlerConfig扫描", config_scan_result))
    
    # 测试4：真实提取模拟
    real_extraction_result = simulate_real_extraction()
    results.append(("真实提取模拟", real_extraction_result))
    
    # 总结
    print("\n📊 测试总结:")
    passed = 0
    for test_name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"  {test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\n🎯 总计: {passed}/{len(results)} 个测试通过")
    
    if passed == len(results):
        print("🎉 所有测试通过！文件路径处理正常。")
    else:
        print("⚠️ 部分测试失败，可能存在文件路径问题。")
    
    return passed == len(results)

if __name__ == "__main__":
    main() 