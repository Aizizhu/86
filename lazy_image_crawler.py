"""Reliable crawler for XC8866 topic pages with front-end lazy-loaded images.

The site renders topic images in Vue/Element Plus markup such as::

    <li><div class="... topic-detail-image"><div class="el-image"><img src="..."></div></div></li>

A plain HTTP request often misses these nodes because they are produced after the
browser runs JavaScript. This crawler therefore uses Playwright to open the real
page, scroll image containers into view, wait for ``img.el-image__preview``
elements, and then exports both page metadata and image URLs.
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import re
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence

import pandas as pd
from bs4 import BeautifulSoup

BASE_URL = "https://xc8866.com/topic/{topic_id:06d}"
DEFAULT_WAIT_SELECTOR = "img.el-image__preview, .topic-detail-image img, .el-image img"
IMAGE_SELECTORS = (
    ".topic-detail-image img",
    "img.el-image__preview",
    ".el-image img",
    "img[src]",
)


@dataclass
class TopicResult:
    topic_id: str
    url: str
    ok: bool
    title: str = ""
    price: str = ""
    address: str = ""
    qq: str = ""
    wechat: str = ""
    phone: str = ""
    content: str = ""
    image_count: int = 0
    image_urls: str = ""
    error: str = ""


def clean_excel_text(value: str) -> str:
    """Remove control characters that Excel writers reject, while preserving CJK text."""
    return re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", value or "")


def build_topic_url(topic_id: int | str) -> str:
    return BASE_URL.format(topic_id=int(topic_id))


def parse_topic_id(url: str) -> str:
    match = re.search(r"/topic/(\d+)", url)
    return match.group(1) if match else ""


def extract_info(soup: BeautifulSoup) -> tuple[str, str, str, str, str]:
    price = address = qq = wechat = phone = ""

    for row in soup.find_all("tr"):
        cells = row.find_all(["td", "th"])
        if len(cells) < 2:
            continue
        key = cells[0].get_text(" ", strip=True)
        value = cells[1].get_text(" ", strip=True)
        if "价格" in key:
            price = value
        elif "地址" in key:
            address = value
        elif "QQ" in key.upper():
            qq = value
        elif "微信" in key:
            wechat = value
        elif "电话" in key or "手机" in key:
            phone = value

    text = soup.get_text("\n", strip=True)
    if not qq:
        qq_match = re.search(r"QQ[:：\s]*([0-9]{5,})", text, re.I)
        qq = qq_match.group(1) if qq_match else ""
    if not phone:
        phone_match = re.search(r"(?:电话|手机)[:：\s]*([0-9+\-\s]{7,})", text)
        phone = phone_match.group(1).strip() if phone_match else ""

    return price, address, qq, wechat, phone


def extract_content(soup: BeautifulSoup) -> str:
    paragraphs = [p.get_text(" ", strip=True) for p in soup.find_all("p")]
    return "\n".join(p for p in paragraphs if p)


def normalize_image_url(page: Any, value: str) -> str:
    if not value:
        return ""
    return page.evaluate("url => new URL(url, location.href).href", value)


def scroll_and_wait_for_lazy_images(page: Any, wait_selector: str, timeout_ms: int) -> None:
    """Trigger lazy loading by scrolling all candidate image containers into view."""
    from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
    page.wait_for_load_state("domcontentloaded", timeout=timeout_ms)
    try:
        page.wait_for_load_state("networkidle", timeout=min(timeout_ms, 8_000))
    except PlaywrightTimeoutError:
        pass

    try:
        page.wait_for_selector(wait_selector, timeout=timeout_ms)
    except PlaywrightTimeoutError:
        # Some pages have no images or render slowly. Continue and parse what exists.
        pass

    locators = [page.locator(selector) for selector in (".topic-detail-image", ".el-image", "img")]
    seen = 0
    for locator in locators:
        count = min(locator.count(), 200)
        for index in range(count):
            try:
                locator.nth(index).scroll_into_view_if_needed(timeout=2_000)
                page.wait_for_timeout(120)
                seen += 1
            except PlaywrightTimeoutError:
                continue
        if seen:
            break

    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    page.wait_for_timeout(500)
    page.evaluate("window.scrollTo(0, 0)")
    page.wait_for_timeout(200)


def extract_image_urls(page: Any) -> list[str]:
    from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

    urls: list[str] = []
    for selector in IMAGE_SELECTORS:
        for image in page.locator(selector).all():
            for attr in ("src", "data-src", "data-original", "data-lazy-src"):
                try:
                    value = image.get_attribute(attr)
                except PlaywrightTimeoutError:
                    value = None
                normalized = normalize_image_url(page, value or "") if value else ""
                if normalized and not normalized.startswith("data:") and normalized not in urls:
                    urls.append(normalized)
    return urls


def crawl_topic(browser: Any, url: str, timeout_ms: int, retries: int) -> TopicResult:
    last_error = ""
    topic_id = parse_topic_id(url)

    for attempt in range(1, retries + 2):
        page = browser.new_page(
            viewport={"width": 1365, "height": 900},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
            ),
        )
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
            scroll_and_wait_for_lazy_images(page, DEFAULT_WAIT_SELECTOR, timeout_ms)

            html = page.content()
            soup = BeautifulSoup(html, "html.parser")
            title_tag = soup.find("h1") or soup.find("title")
            title = title_tag.get_text(" ", strip=True) if title_tag else ""
            price, address, qq, wechat, phone = extract_info(soup)
            content = extract_content(soup)
            image_urls = extract_image_urls(page)

            if not title and not image_urls:
                raise RuntimeError("no title and no image URLs found after rendering")

            return TopicResult(
                topic_id=topic_id,
                url=url,
                ok=True,
                title=clean_excel_text(title),
                price=clean_excel_text(price),
                address=clean_excel_text(address),
                qq=clean_excel_text(qq),
                wechat=clean_excel_text(wechat),
                phone=clean_excel_text(phone),
                content=clean_excel_text(content),
                image_count=len(image_urls),
                image_urls="\n".join(image_urls),
            )
        except Exception as exc:  # noqa: BLE001 - keep crawler running and report per URL.
            last_error = f"attempt {attempt}: {exc}"
            if attempt <= retries:
                time.sleep(1.5 * attempt + random.random())
        finally:
            page.close()

    return TopicResult(topic_id=topic_id, url=url, ok=False, error=clean_excel_text(last_error))


def iter_urls(args: argparse.Namespace) -> list[str]:
    urls: list[str] = []
    if args.url:
        urls.extend(args.url)
    if args.url_file:
        urls.extend(line.strip() for line in Path(args.url_file).read_text(encoding="utf-8").splitlines())
    if args.start_id is not None and args.end_id is not None:
        urls.extend(build_topic_url(topic_id) for topic_id in range(args.start_id, args.end_id + 1))
    return [url for url in dict.fromkeys(urls) if url]


def save_results(results: Sequence[TopicResult], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    rows = [asdict(result) for result in results]
    if output.suffix.lower() == ".json":
        output.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    elif output.suffix.lower() == ".csv":
        with output.open("w", encoding="utf-8-sig", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=list(TopicResult.__dataclass_fields__.keys()))
            writer.writeheader()
            writer.writerows(rows)
    else:
        pd.DataFrame(rows).to_excel(output, index=False)


def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="XC8866 lazy-loaded topic image crawler")
    parser.add_argument("--url", action="append", help="Topic URL. Can be supplied multiple times.")
    parser.add_argument("--url-file", help="Text file containing one topic URL per line.")
    parser.add_argument("--start-id", type=int, help="Start topic ID, inclusive.")
    parser.add_argument("--end-id", type=int, help="End topic ID, inclusive.")
    parser.add_argument("--output", default="lazy_image_results.xlsx", help="Output .xlsx, .csv, or .json file.")
    parser.add_argument("--headful", action="store_true", help="Show the browser window for debugging.")
    parser.add_argument("--timeout", type=int, default=30_000, help="Per-page timeout in milliseconds.")
    parser.add_argument("--retries", type=int, default=2, help="Retry count after the first attempt.")
    return parser.parse_args(argv)


def main(argv: Iterable[str] | None = None) -> int:
    args = parse_args(argv)
    urls = iter_urls(args)
    if not urls:
        raise SystemExit("Please provide --url, --url-file, or --start-id/--end-id.")

    from playwright.sync_api import sync_playwright

    results: list[TopicResult] = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=not args.headful)
        try:
            for index, url in enumerate(urls, 1):
                print(f"[{index}/{len(urls)}] crawling {url}")
                result = crawl_topic(browser, url, args.timeout, args.retries)
                status = "OK" if result.ok else "FAIL"
                print(f"  {status}: images={result.image_count} title={result.title or result.error}")
                results.append(result)
                save_results(results, Path(args.output))
        finally:
            browser.close()

    save_results(results, Path(args.output))
    print(f"Saved {len(results)} rows to {args.output}")
    failed = sum(1 for item in results if not item.ok)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
