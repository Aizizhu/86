# XC8866 爬虫工具说明

本项目包含两个配套爬虫脚本与两个一键启动 `bat`：

- `crawler.py`：按帖子 ID 区间批量抓取主数据。
- `retry_failed.py`：读取第一次失败链接并进行二次重试。
- `run.bat`：一键启动主爬虫（自动建虚拟环境 + 安装依赖）。
- `run_repeat.bat`：一键启动失败重试爬虫（同样自动处理环境）。

---

## 1. 文件结构

- `crawler.py`：主爬虫
- `retry_failed.py`：失败重试爬虫
- `run.bat`：启动 `crawler.py`
- `run_repeat.bat`：启动 `retry_failed.py`
- `requirements.txt`：依赖列表
- `README.md`：使用说明

---

## 2. 主爬虫 `crawler.py` 功能

启动后会提示输入：

1. 起始 ID（如 `84750`）
2. 结束 ID（如 `182467`）
3. 线程数（默认 `20`）

### 抓取地址规则

主爬虫会按以下格式拼接链接并请求：

- `https://xc8866.com/topic/{tid:06d}`

例如 ID 为 `123` 时会访问：

- `https://xc8866.com/topic/000123`

### 页面解析内容

每个帖子会提取以下字段并写入 Excel：

- 标题（`h1`）
- 价格
- 地址
- QQ
- 微信
- 电话/手机
- 正文（所有 `p` 标签文本合并）
- 链接

### 运行过程特性

- 多线程并发抓取（`ThreadPoolExecutor`）
- 控制台实时显示：成功数、失败数、进度、速度、预计剩余时间
- 每成功 `100` 条自动保存一次
- 程序结束后再次保存最终结果
- 失败链接会写入 `failed_links.txt`

### 主爬虫输出文件

- `xc8866.xlsx`：主爬虫抓取结果
- `failed_links.txt`：主爬虫失败链接（每次启动会先清空再重新记录）

---

## 3. 失败重试爬虫 `retry_failed.py` 功能

该脚本用于处理主爬虫失败的数据。

启动后会提示输入：

1. 线程数（默认 `10`）

### 重试流程

1. 读取 `failed_links.txt` 中的所有链接。
2. 多线程重新抓取。
3. 成功数据写入 `retry_result.xlsx`。
4. 仍失败的链接写入 `failed_retry_failed.txt`。

### 重试脚本特性

- 每成功 `50` 条自动保存一次
- 结束后保存完整结果
- 控制台显示成功/失败与速度统计

### 重试爬虫输出文件

- `retry_result.xlsx`：重试成功数据
- `failed_retry_failed.txt`：重试后仍失败的链接

---

## 4. `run.bat` 与 `run_repeat.bat` 启动逻辑

两个 bat 的核心逻辑一致，仅最后启动的 Python 脚本不同。

### 自动化步骤

1. 切换到 bat 所在目录。
2. 检测本地是否有 `py` 启动器，有则优先使用 `py`，否则使用 `python`。
3. 若不存在 `.venv\Scripts\activate.bat`：
   - 自动创建虚拟环境 `.venv`
   - 激活虚拟环境
   - 自动执行：
     - `python -m pip install --upgrade pip`
     - `python -m pip install -r requirements.txt`
4. 若已存在虚拟环境则直接激活。
5. 启动目标脚本：
   - `run.bat` -> `python crawler.py`
   - `run_repeat.bat` -> `python retry_failed.py`
6. 输出执行结果（成功/失败退出码）并 `pause` 停留窗口。

### 适合使用方式

- 第一次运行：直接双击 `run.bat`
- 主爬虫跑完后：双击 `run_repeat.bat` 对失败链接补抓

---

## 5. 环境要求

- Windows（使用 bat 一键运行）
- Python 3.9+（建议）
- 可访问目标站点网络

依赖安装（手动方式）：

```bash
pip install -r requirements.txt
```

---

## 6. 推荐执行顺序

1. 运行 `run.bat` 做主爬取。
2. 检查 `xc8866.xlsx` 与 `failed_links.txt`。
3. 运行 `run_repeat.bat` 重试失败链接。
4. 合并查看 `retry_result.xlsx` 与 `failed_retry_failed.txt`。

---

## 7. 注意事项

- 线程数过大可能导致请求失败增多，建议逐步调优。
- `crawler.py` 每次运行会清空 `failed_links.txt`，请在新任务前先备份旧失败记录（如需要）。
- 目标站点结构变化时，字段提取逻辑可能需要调整。

---

## 8. 懒加载图片渲染爬虫 `lazy_image_crawler.py`

`xc8866.com/topic/{id}` 的图片节点通常由前端渲染生成，例如页面内会出现类似：

```html
<div class="topic-detail-image">
  <div class="el-image">
    <img class="el-image__inner el-image__preview" src="https://...">
  </div>
</div>
```

这类节点不一定存在于第一次 HTTP 返回的静态 HTML 中，因此只用 `requests` / `cloudscraper` 可能抓不到图片。`lazy_image_crawler.py` 使用 Playwright 启动真实 Chromium：

1. 打开帖子页面并等待 DOM 加载。
2. 等待 `.topic-detail-image img`、`img.el-image__preview` 或 `.el-image img` 出现。
3. 逐个滚动图片容器，触发懒加载。
4. 提取 `src`、`data-src`、`data-original`、`data-lazy-src` 等图片地址。
5. 输出标题、联系信息、正文、图片数量和图片 URL。
6. 每抓完一个页面就增量保存一次，降低中途失败的数据损失。

### 首次安装

```bash
pip install -r requirements.txt
playwright install chromium
```

### 抓单个帖子

```bash
python lazy_image_crawler.py --url https://xc8866.com/topic/192878 --output lazy_image_results.xlsx
```

### 按 ID 区间抓取

```bash
python lazy_image_crawler.py --start-id 192878 --end-id 192900 --output lazy_image_results.xlsx
```

### 从 URL 文件抓取

```bash
python lazy_image_crawler.py --url-file urls.txt --output lazy_image_results.csv
```

### 调试模式

如果需要观察浏览器实际加载过程，可以加 `--headful`：

```bash
python lazy_image_crawler.py --url https://xc8866.com/topic/192878 --headful --output lazy_image_results.json
```

### 输出字段

- `topic_id`：帖子 ID
- `url`：帖子链接
- `ok`：是否抓取成功
- `title`：标题
- `price` / `address` / `qq` / `wechat` / `phone`：结构化信息
- `content`：正文段落
- `image_count`：图片数量
- `image_urls`：图片地址，多个地址以换行分隔
- `error`：失败原因

### 可靠性建议

- 首次运行必须执行 `playwright install chromium`，否则本机没有浏览器可用。
- 如果页面加载慢，可调大超时时间，例如 `--timeout 60000`。
- 如果目标站限制频繁访问，建议分批运行 ID 区间，避免持续高频请求。
- 若只想保存图片链接，优先使用 `.csv` 或 `.json`，后续处理更方便。
