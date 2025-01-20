import asyncio
import requests_async

urls = [
    {"name": "迁改数字化", "urls": ["http://mall.maiduoyu.com/#/home"]},
    {"name": "广工大", "urls": ["http://mall.maiduoyu.com"]},
    {"name": "运距", "urls": ["http://47.99.89.20"]},
    {"name": "动态增容", "urls": ["http://47.99.89.20:8895/login", "http://47.97.193.209:8080/eos/smain"]},
    {"name": "投标系统", "urls": ["http://47.99.89.20:8886/home"]},
    {"name": "省巡飞", "urls": ["http://47.99.89.20:8198/"]},
    {"name": "资料管理平台", "urls": ["http://suidaoke.maiduoyu.com"]},
    {"name": "项目进度可视化", "urls": ["http://47.99.89.20:8398/"]}
]

async def check_url(url_obj):
    try:
        response = await requests_async.get(url_obj['url'], timeout=5)
        if response.status_code == 200:
            url_obj['result'] = '可访问'
        else:
            url_obj['result'] = '不可访问'
    except requests_async.RequestException as e:
        url_obj['result'] = '不可访问'
    return url_obj

async def main():
    tasks = []
    results = []
    for item in urls:
        print(f"检查 {item['name']} 的网址:")
        for url in item['urls']:
            url_obj = {
                "name": item['name'],
                "url": url,
            }
            tasks.append(check_url(url_obj))
    results = await asyncio.gather(*tasks)
    print(results)

asyncio.run(main())