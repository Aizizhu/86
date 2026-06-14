# XC8866 爬虫工具说明

本项目包含三类爬虫脚本：

| 脚本 | 适用场景 | 主要输出 |
| --- | --- | --- |
| `crawler.py` | 按帖子 ID 区间批量抓取静态字段 | `xc8866.xlsx`、`failed_links.txt` |
| `retry_failed.py` | 对 `crawler.py` 失败链接做二次重试 | `retry_result.xlsx`、`failed_retry_failed.txt` |
| `lazy_image_crawler.py` | 抓取前端懒加载图片、分页列表页、图片下载/嵌入 Excel | `result.xlsx` / `.csv` / `.json`、`img/{帖子ID}/`、`failed_links.txt` |

如果你的目标是抓取帖子里的图片，尤其是类似下面这种由前端渲染出来的图片节点，建议优先使用 `lazy_image_crawler.py`：

```html
<li>
  <div class="topic-detail-image">
    <div class="el-image">
      <img class="el-image__inner el-image__preview" src="https://...">
    </div>
  </div>
</li>
```

---

## 1. 文件结构

- `crawler.py`：原始主爬虫，按帖子 ID 区间抓取文本字段。
- `retry_failed.py`：读取 `failed_links.txt` 并重试失败帖子。
- `lazy_image_crawler.py`：增强爬虫，支持 Playwright 渲染、懒加载图片、列表页分页、断点续跑、图片下载和 Excel 嵌图。
- `run.bat`：Windows 一键启动 `crawler.py`。
- `run_repeat.bat`：Windows 一键启动 `retry_failed.py`。
- `requirements.txt`：Python 依赖列表。
- `README.md`：使用说明。

---

## 2. 环境准备

### 2.1 安装 Python 依赖

建议使用 Python 3.9+。

```bash
pip install -r requirements.txt
```

### 2.2 安装 Playwright 浏览器内核

只有 `lazy_image_crawler.py` 的真实浏览器渲染模式需要这一步。首次使用必须执行：

```bash
playwright install chromium
```

如果你只使用 `crawler.py` / `retry_failed.py`，或只使用 `lazy_image_crawler.py --static-only`，可以不安装 Chromium。

---

## 3. 推荐用法：懒加载图片爬虫 `lazy_image_crawler.py`

`lazy_image_crawler.py` 适合解决静态请求抓不到图片的问题。它会打开真实 Chromium 页面，等待并滚动 `.topic-detail-image`、`.el-image`、`img` 等节点，触发懒加载后再提取图片。

### 3.1 它会抓取哪些内容

每条帖子会输出：

- `topic_id`：帖子 ID
- `url`：帖子链接
- `ok`：是否成功
- `title`：标题
- `price`：价格
- `address`：地址
- `qq`：QQ
- `wechat`：微信
- `phone`：电话/手机
- `content`：正文
- `image_count`：图片数量
- `image_urls`：图片链接，多个链接以换行分隔
- `error`：失败原因

### 3.2 图片过滤规则

图片提取逻辑已融入原脚本规则：

1. 优先只从帖子图片区块中找：`.topic-detail-image`。
2. 读取 `src`、`data-src`、`data-original`、`data-lazy-src`。
3. 排除头像地址，例如包含 `/avatars/` 的图片。
4. 排除常见占位图：`zwzp.jpg`、`default.jpg`、`nopic.jpg`。
5. 排除 class 中包含 `avatar` 的 UI 图片。
6. 默认最多保留 `4` 张图片，可用 `--image-limit` 调整。

### 3.3 抓单个帖子

```bash
python lazy_image_crawler.py --url https://xc8866.com/topic/192878 --output result.xlsx
```

### 3.4 抓单个帖子并下载图片、嵌入 Excel

```bash
python lazy_image_crawler.py --url https://xc8866.com/topic/192878 --output result.xlsx
```

说明：

- 图片会下载到 `img/{帖子ID}/` 目录，例如 `img/192878/01_标题.jpg`。
- Excel 第 9 列开始会插入图片。
- 默认会下载图片并插入 Excel；如果只需要图片链接，请加 `--no-embed-images`，速度会更快。

### 3.5 按帖子 ID 区间抓取

```bash
python lazy_image_crawler.py --start-id 192878 --end-id 192900 --output result.xlsx
```

### 3.6 从 URL 文件抓取

准备 `urls.txt`，每行一个帖子链接：

```text
https://xc8866.com/topic/192878
https://xc8866.com/topic/192879
```

运行：

```bash
python lazy_image_crawler.py --url-file urls.txt --output result.csv
```

### 3.7 从列表页分页抓取

适合从分类页、列表页批量发现帖子链接：

```bash
python lazy_image_crawler.py --start-url https://xc8866.com/some/list/path --total-pages 10 --page-threads 4 --output result.xlsx --resume
```

参数说明：

- `--start-url`：列表页第一页 URL。
- `--total-pages`：需要抓取的列表页总页数。
- `--page-threads`：列表页并发请求数，默认 `4`。
- `--resume`：启用断点续跑，跳过 `progress.json` 中已完成的列表页。
- `--progress-file`：自定义进度文件，默认 `progress.json`。

列表页 URL 会按以下规则构造：

- 如果 URL 已有 `page=数字`，则替换该页码。
- 如果 URL 有其他查询参数，则追加 `&page=页码`。
- 如果 URL 没有查询参数，则追加 `?page=页码`。

### 3.8 静态模式

如果页面源码本身已经包含图片节点，或者当前机器无法安装 Chromium，可以使用静态模式：

```bash
python lazy_image_crawler.py --url https://xc8866.com/topic/192878 --static-only --output result.xlsx
```

注意：静态模式不会执行页面 JavaScript，因此遇到前端渲染图片时可能抓不到图。

### 3.9 调试模式

如果想观察浏览器实际加载和滚动过程：

```bash
python lazy_image_crawler.py --url https://xc8866.com/topic/192878 --headful --output result.json
```

### 3.10 常用参数速查

| 参数 | 默认值 | 说明 |
| --- | --- | --- |
| `--url` | 无 | 指定单个帖子 URL，可重复传入多次。 |
| `--url-file` | 无 | 从文本文件读取帖子 URL。 |
| `--start-id` / `--end-id` | 无 | 按帖子 ID 区间构造 URL。 |
| `--start-url` / `--total-pages` | 无 | 从列表页分页发现帖子 URL。 |
| `--output` | `result.xlsx` | 输出文件，支持 `.xlsx`、`.csv`、`.json`。 |
| `--embed-images` | 开启 | 下载图片并嵌入 `.xlsx`；默认开启。 |
| `--no-embed-images` | 关闭 | 不下载/不嵌入图片，只写入图片 URL。 |
| `--image-dir` | `img` | 图片下载根目录，按 `img/{帖子ID}/` 分目录保存。 |
| `--image-limit` | `4` | 每个帖子最多保留的图片数量。 |
| `--failed-file` | `failed_links.txt` | 失败帖子 URL 输出文件。 |
| `--timeout` | `30000` | 单页超时时间，单位毫秒。 |
| `--retries` | `2` | 每个帖子失败后的重试次数。 |
| `--page-delay` | `1.0` | 列表页批次之间的等待秒数。 |
| `--topic-delay` | `0.2` | 帖子抓取之间的等待秒数。 |
| `--static-only` | 关闭 | 不使用 Playwright，只抓静态 HTML。 |
| `--headful` | 关闭 | 显示浏览器窗口，方便调试。 |
| `--threads` | `6` | 兼容原脚本参数；帖子渲染阶段为保证稳定性保持顺序执行。 |

---

## 4. 原始主爬虫 `crawler.py`

`crawler.py` 适合只抓取帖子文本字段，不处理前端懒加载图片。

启动后会提示输入：

1. 起始 ID，例如 `84750`
2. 结束 ID，例如 `182467`
3. 线程数，默认 `20`

### 抓取地址规则

主爬虫会按以下格式拼接链接并请求：

```text
https://xc8866.com/topic/{tid:06d}
```

例如 ID 为 `123` 时会访问：

```text
https://xc8866.com/topic/000123
```

### 输出文件

- `xc8866.xlsx`：抓取结果。
- `failed_links.txt`：失败链接，每次启动会先清空再重新记录。

---

## 5. 失败重试爬虫 `retry_failed.py`

`retry_failed.py` 用于处理 `crawler.py` 产生的失败链接。

启动后会提示输入线程数，默认 `10`。

流程：

1. 读取 `failed_links.txt`。
2. 多线程重新抓取。
3. 成功数据写入 `retry_result.xlsx`。
4. 仍失败的链接写入 `failed_retry_failed.txt`。

---

## 6. Windows 一键启动脚本

项目保留两个 Windows `bat`：

- `run.bat`：启动 `crawler.py`。
- `run_repeat.bat`：启动 `retry_failed.py`。

它们会自动：

1. 切换到 bat 所在目录。
2. 检测 `py` 或 `python`。
3. 创建并激活 `.venv`。
4. 执行 `pip install -r requirements.txt`。
5. 启动对应 Python 脚本。
6. 执行结束后 `pause` 停留窗口。

---

## 7. 推荐执行顺序

### 只抓文本字段

1. 双击或运行 `run.bat`。
2. 检查 `xc8866.xlsx` 和 `failed_links.txt`。
3. 双击或运行 `run_repeat.bat` 重试失败链接。
4. 查看 `retry_result.xlsx` 和 `failed_retry_failed.txt`。

### 抓懒加载图片

1. 执行 `pip install -r requirements.txt`。
2. 执行 `playwright install chromium`。
3. 用 `lazy_image_crawler.py` 抓单帖、ID 区间、URL 文件或列表页。
4. 默认会把图片下载到 `img/{帖子ID}/` 并插入 Excel；如只要 URL，加 `--no-embed-images`。
5. 如目标站访问频繁失败，调大 `--topic-delay`、`--page-delay`、`--timeout`。

---

## 8. 常见问题

### 为什么普通爬虫抓不到图片？

因为部分图片节点由前端 JavaScript 渲染，第一次 HTTP 返回的 HTML 里可能没有最终的 `<img src="...">`。`lazy_image_crawler.py` 使用真实 Chromium 渲染页面并滚动触发懒加载，所以更适合这类页面。

### 为什么 `--threads` 没有让帖子渲染并发？

Playwright 浏览器渲染并发过高时更容易被目标站限制，也更容易出现浏览器上下文不稳定。当前脚本保留 `--threads` 作为兼容参数，列表页并发由 `--page-threads` 控制，帖子渲染阶段默认顺序执行以提高稳定性。

### 抓取很慢怎么办？

可以先加 `--no-embed-images`，只导出图片 URL；确认结果稳定后再使用默认嵌图模式下载图片。也可以降低抓取范围，分批运行。

### Excel 无法打开或图片显示异常怎么办？

通常是图片下载不完整或源站返回了非图片内容。可以删除 `img/{帖子ID}/` 中对应文件后重跑，或先加 `--no-embed-images` 导出 `.csv` / `.json` 检查图片 URL。

---

## 9. 注意事项

- 线程数和访问频率过高可能导致请求失败增多，建议逐步调优。
- `crawler.py` 每次运行会清空 `failed_links.txt`，新任务前请按需备份。
- 使用 `lazy_image_crawler.py --resume` 时，进度默认保存在 `progress.json`。
- 目标站点结构变化时，字段和图片提取逻辑可能需要同步调整。
