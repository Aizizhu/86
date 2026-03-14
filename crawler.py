import re
import threading
from concurrent.futures import ThreadPoolExecutor

import pandas as pd
import requests
from bs4 import BeautifulSoup

print("==============================")
print("XC8866 帖子爬虫（稳定版）")
print("==============================")

start_id = int(input("起始ID(如84750): "))
end_id = int(input("结束ID(如182467): "))
threads = input("线程数(默认12): ")

if threads.strip() == "":
    threads = 12
else:
    threads = int(threads)

headers = {"User-Agent": "Mozilla/5.0"}

lock = threading.Lock()

save_file = "xc8866帖子.xlsx"
fail_file = "retry.txt"

results = []
visited = set()

# 读取已存在数据，实现断点续爬
try:
    old = pd.read_excel(save_file)
    visited = set(old["链接"].tolist())
    results = old.to_dict("records")
    print("已加载历史数据:", len(results))
except Exception:
    pass


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


def save_excel():
    df = pd.DataFrame(results)
    df.to_excel(save_file, index=False)


def crawl(tid):
    url = f"https://xc8866.com/topic/{tid:06d}"

    if url in visited:
        return

    try:
        r = requests.get(url, headers=headers, timeout=10)

        if r.status_code != 200:
            return

        soup = BeautifulSoup(r.text, "html.parser")

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
            visited.add(url)

            count = len(results)

            print("完成:", tid, "总:", count)

            if count % 100 == 0:
                save_excel()
                print("自动保存:", count)

    except Exception:
        with open(fail_file, "a", encoding="utf8") as f:
            f.write(str(tid) + "\n")

        print("失败:", tid)


print("\n===== 开始爬取 =====\n")

ids = range(start_id, end_id + 1)

with ThreadPoolExecutor(max_workers=threads) as pool:
    pool.map(crawl, ids)

save_excel()

print("\n===== 爬取完成 =====")
print("数据保存:", save_file)
