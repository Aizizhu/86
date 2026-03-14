import re
import threading
from concurrent.futures import ThreadPoolExecutor

import cloudscraper
import pandas as pd
from bs4 import BeautifulSoup

print("==============================")
print("XC8866 帖子爬虫")
print("==============================")

start_id = int(input("起始ID(如84750): "))
end_id = int(input("结束ID(如182467): "))
threads = int(input("线程数(建议20): "))

scraper = cloudscraper.create_scraper()
lock = threading.Lock()
results = []


def extract_info(text):
    price = ""
    address = ""
    qq = ""
    wechat = ""
    phone = ""

    m = re.search(r"价格[:： ]?([^\n ]+)", text)
    if m:
        price = m.group(1)

    m = re.search(r"地址[:： ]?([^\n]+)", text)
    if m:
        address = m.group(1)

    m = re.search(r"QQ[:： ]?([0-9]{5,12})", text)
    if m:
        qq = m.group(1)

    m = re.search(r"微信[:： ]?([a-zA-Z0-9_-]+)", text)
    if m:
        wechat = m.group(1)

    m = re.search(r"1[3-9][0-9]{9}", text)
    if m:
        phone = m.group(0)

    return price, address, qq, wechat, phone


def crawl(tid):
    url = f"https://xc8866.com/topic/{tid:06d}"

    try:
        response = scraper.get(url, timeout=15)

        if response.status_code != 200:
            return

        soup = BeautifulSoup(response.text, "html.parser")
        title_tag = soup.find("h1")

        if not title_tag:
            return

        title = title_tag.text.strip()
        text = soup.get_text("\n")
        price, address, qq, wechat, phone = extract_info(text)

        data = {
            "标题": title,
            "价格": price,
            "地址": address,
            "QQ": qq,
            "微信": wechat,
            "电话": phone,
            "正文": text.strip(),
            "链接": url,
        }

        with lock:
            results.append(data)
            print("完成:", tid, "总:", len(results))

            if len(results) % 100 == 0:
                df = pd.DataFrame(results)
                df.to_excel("xc8866.xlsx", index=False)
                print("自动保存")

    except Exception:
        print("失败:", tid)


print("\n===== 开始爬取 =====\n")

ids = range(start_id, end_id + 1)

with ThreadPoolExecutor(max_workers=threads) as pool:
    pool.map(crawl, ids)

df = pd.DataFrame(results)
df.to_excel("xc8866.xlsx", index=False)

print("\n完成")
