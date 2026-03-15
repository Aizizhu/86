# 帖子爬虫

按帖子 ID 区间抓取 `https://example.com/topic/{id}` 页面，并导出为 Excel。

## 功能

- 输入起始 ID、结束 ID、线程数后并发抓取。
- 自动提取字段：标题、价格、地址、QQ、微信、电话、正文、链接。
- 每抓取 100 条自动保存一次，结束后再保存完整结果到 `posts.xlsx`。

## 环境

- Python 3.9+

安装依赖：

```bash
pip install -r requirements.txt
```

## 运行

```bash
python crawler.py
```

脚本会交互式询问：

- 起始 ID（如 `84750`）
- 结束 ID（如 `182467`）
- 线程数（建议 `20`）

## 输出

- `posts.xlsx`
