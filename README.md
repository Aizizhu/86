# xc8866 爬虫使用说明

这是一个用于抓取 `xc8866` 列表页帖子信息并导出到 Excel 的脚本。

## 功能简介

- 从指定列表页开始按分页抓取帖子。
- 自动解析标题、价格、地址、QQ、微信、电话、正文和链接。
- 结果写入 `result.xlsx`。
- 使用 `progress.json` 记录已完成页面，支持中断后继续。

## 环境要求

- Python 3.9+
- pip

## 1. 创建并激活虚拟环境（venv）

在项目根目录执行：

```bash
python3 -m venv .venv
source .venv/bin/activate
```

> Windows PowerShell 可使用：
>
> ```powershell
> py -m venv .venv
> .\.venv\Scripts\Activate.ps1
> ```

## 2. 安装依赖库

### 方式 A：使用 requirements.txt（推荐）

```bash
pip install -r requirements.txt
```

### 方式 B：手动安装

```bash
pip install requests beautifulsoup4 openpyxl
```

## 3. 运行脚本

```bash
python crawler.py
```

常用参数：

```bash
python crawler.py \
  --start-url "https://xc8866.com/?page=1" \
  --total-pages 20 \
  --page-threads 4 \
  --threads 6
```

参数说明：

- `--start-url`：起始列表页 URL。
- `--total-pages`：总页数；不传时自动探测。
- `--page-threads`：列表页并发数（批次并发）。
- `--threads`：帖子详情页并发数。

## 输出文件

- `result.xlsx`：抓取结果。
- `progress.json`：已完成页面进度。

## 常见问题

- 如果出现编码异常或网络超时，可降低并发参数：`--page-threads` 和 `--threads`。
- 若想重新全量抓取，可删除 `progress.json` 后重跑。
