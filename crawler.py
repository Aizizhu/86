import cloudscraper
import threading
import pandas as pd
import time
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor
import re

print("==============================")
print("XC8866 监控版爬虫")
print("==============================")

start_id = int(input("起始ID(如84750): "))
end_id = int(input("结束ID(如182467): "))

try:
    threads = int(input("线程数(默认20): ") or 20)
except:
    threads = 20

scraper = cloudscraper.create_scraper()

lock = threading.Lock()

results = []
visited = set()

success_count = 0
fail_count = 0

total_tasks = end_id - start_id + 1

start_time = time.time()

save_file = "xc8866.xlsx"
failed_file = "failed_links.txt"  # 文件名用于记录失败的链接


# 解析表格信息
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


# 保存Excel
def save_excel():
    cleaned_results = [
        dict(map(lambda item: (item[0], clean_data(item[1])), item.items()))
        for item in results
    ]

    df = pd.DataFrame(cleaned_results)
    df.to_excel(save_file, index=False)
    print(f"\n💾 已保存 {len(results)} 条数据\n")


# 清理非法字符
def clean_data(value):
    if isinstance(value, str):
        return re.sub(r'[^\x20-\x7E]', '', value)

    return value


# 记录失败的链接到文本文件
def log_failed_url(url):
    with open(failed_file, "a", encoding="utf-8") as file:
        file.write(url + "\n")


def crawl(tid):
    global success_count, fail_count

    url = f"https://xc8866.com/topic/{tid:06d}"

    try:
        r = scraper.get(url, timeout=15)

        if r.status_code != 200:
            raise Exception(f"Status Code: {r.status_code}")

        soup = BeautifulSoup(r.text, "html.parser")

        title_tag = soup.find("h1")

        if not title_tag:
            raise Exception("No Title Found")

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
            "链接": url
        }

        with lock:
            results.append(data)
            success_count += 1

            done = success_count + fail_count
            progress = done / total_tasks * 100
            elapsed = time.time() - start_time
            speed = success_count / elapsed * 3600 if elapsed > 0 else 0
            remain = (total_tasks - done) / (success_count / elapsed) if success_count > 0 else 0

            print(
                f"[成功] ID:{tid} | 成功:{success_count} | 失败:{fail_count} | "
                f"进度:{progress:.2f}% | 速度:{speed:.0f}帖/小时 | "
                f"剩余:{remain/3600:.2f}小时"
            )

            if success_count % 100 == 0:
                save_excel()

    except Exception as e:
        with lock:
            fail_count += 1
            print(f"[失败] ID:{tid} | 失败总数:{fail_count} | 错误: {e}")
            log_failed_url(url)  # 记录失败的链接


print("\n===== 开始爬取 =====\n")

ids = range(start_id, end_id + 1)

# 确保在程序开始时清空之前的失败链接记录
with open(failed_file, "w", encoding="utf-8") as file:
    file.write("")

with ThreadPoolExecutor(max_workers=threads) as pool:
    pool.map(crawl, ids)

save_excel()

print("\n===== 爬取完成 =====")
