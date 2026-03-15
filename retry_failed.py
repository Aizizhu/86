import cloudscraper
import threading
import pandas as pd
import time
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor
import re
import requests

print("==============================")
print("XC8866 失败链接重试爬虫")
print("==============================")

try:
    threads = int(input("线程数(默认10): ") or 10)
except Exception:
    threads = 10

failed_file = "failed_links.txt"
retry_fail_file = "failed_retry_failed.txt"
save_file = "retry_result.xlsx"

scraper = cloudscraper.create_scraper()

lock = threading.Lock()

results = []
success_count = 0
fail_count = 0

start_time = time.time()


# 解析表格
def extract_info(soup):
    price = ""
    address = ""
    qq = ""
    wechat = ""
    phone = ""

    rows = soup.find_all("tr")
    for row in rows:
        tds = row.find_all("td")
        if len(tds) != 2:
            continue

        key = tds[0].get_text(strip=True)
        value = tds[1].get_text(strip=True)

        if "价格" in key:
            price = value
        elif "地址" in key:
            address = value
        elif "QQ" in key:
            qq = value
        elif "微信" in key:
            wechat = value
        elif "电话" in key or "手机" in key:
            phone = value

    return price, address, qq, wechat, phone


# 解析正文
def extract_content(soup):
    content_list = []
    ps = soup.find_all("p")
    for p in ps:
        text = p.get_text(strip=True)
        if text:
            content_list.append(text)

    return "\n".join(content_list)


# 清理非法字符
def clean_data(value):
    if isinstance(value, str):
        return re.sub(r"[^\x20-\x7E]", "", value)
    return value


# 保存Excel
def save_excel():
    df = pd.DataFrame(results)

    # 清理数据
    df = df.applymap(clean_data)

    df.to_excel(save_file, index=False)
    print(f"\n💾 已保存 {len(results)} 条数据\n")


# 记录失败的链接
def log_retry_fail(url):
    with open(retry_fail_file, "a", encoding="utf-8") as f:
        f.write(url + "\n")


# 爬取单个链接
def crawl(url):
    global success_count, fail_count
    try:
        r = scraper.get(url, timeout=15)
        r.raise_for_status()

        soup = BeautifulSoup(r.text, "html.parser")
        title_tag = soup.find("h1")

        if not title_tag:
            raise Exception("No title found")

        title = title_tag.get_text(strip=True)
        price, address, qq, wechat, phone = extract_info(soup)
        content = extract_content(soup)

        data = {
            "标题": title,
            "价格": price,
            "地址": address,
            "QQ": qq,
            "微信": wechat,
            "电话": phone,
            "正文": content,
            "链接": url,
        }

        with lock:
            results.append(data)
            success_count += 1
            elapsed = time.time() - start_time
            speed = success_count / elapsed * 3600 if elapsed > 0 else 0
            print(f"[成功] {url} | 成功:{success_count} | 失败:{fail_count} | 速度:{speed:.0f}/小时")

            if success_count % 50 == 0:
                save_excel()

    except requests.exceptions.RequestException as e:
        with lock:
            fail_count += 1
            print(f"[请求失败] {url} | 错误: {e}")
            log_retry_fail(url)

    except Exception as e:
        with lock:
            fail_count += 1
            print(f"[错误] {url} | 错误: {e}")
            log_retry_fail(url)


print("\n读取失败链接...")

with open(failed_file, "r", encoding="utf-8") as f:
    urls = [i.strip() for i in f if i.strip()]

print(f"需要重试 {len(urls)} 条\n")

with ThreadPoolExecutor(max_workers=threads) as pool:
    pool.map(crawl, urls)

save_excel()

print("\n===== 重试完成 =====")
print(f"成功:{success_count} 失败:{fail_count}")
