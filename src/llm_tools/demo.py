import requests
import json
import datetime
import time

def crawl_links():
    """
    从 https://stockjs.jrj.com.cn/share/news/yaowen/yw{date}.js?_={timestamp} 获取信息，
    提取新闻链接，返回链接列表。
    """
    date = datetime.date.today().strftime("%Y-%m-%d")
    timestamp = int(time.time() * 1000)
    url = f"https://stockjs.jrj.com.cn/share/news/yaowen/yw{date}.js?_={timestamp}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # 检查请求是否成功
        response.encoding = 'utf-8'  # 设置编码
        print(response.text)
        data = json.loads(response.text)  # 去掉第一个字符
        links = [item["infourl"] for item in data["newsinfo"]]
        return links
    except requests.exceptions.RequestException as e:
        print(f"请求错误: {e}")
        return []
    except json.JSONDecodeError as e:
        print(f"JSON 解析错误: {e}")
        return []
    except KeyError as e:
        print(f"KeyError: {e}")
        return []

if __name__ == '__main__':
    links = crawl_links()
    for link in links:
        print(link)