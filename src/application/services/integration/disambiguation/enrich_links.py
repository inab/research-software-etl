import requests
import urllib.parse
import os
import logging
import json
import re
from readability import Document
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright
from infrastructure.external.clients import ExternalClients

SOURCEFORGE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; SourceForgeMetadataImporter/1.0)",
    "Accept-Language": "en-US,en;q=0.9",
}


def create_sourceforge_session() -> requests.Session:
    session = requests.Session()
    session.headers.update(SOURCEFORGE_HEADERS)
    return session


def fetch_sourceforge_html(url: str, max_retries: int = 5, base_delay: int = 10, timeout: int = 30) -> str | None:
    import random
    import time

    session = create_sourceforge_session()

    for attempt in range(max_retries):
        try:
            response = session.get(url, timeout=timeout)
            logging.info(f"SourceForge GET {url} -> {response.status_code}")
        except requests.RequestException as e:
            sleep_time = base_delay * (2 ** attempt) + random.uniform(0, 2)
            logging.warning(f"SourceForge request failed for {url}: {e}")
            logging.info(f"Sleeping {sleep_time:.2f}s before retry")
            time.sleep(sleep_time)
            continue

        if response.status_code == 200:
            html = response.text
            if "Just a moment..." in html or "Enable JavaScript and cookies to continue" in html:
                logging.warning(f"SourceForge returned Cloudflare challenge page for {url}")
                sleep_time = base_delay * (2 ** attempt) + random.uniform(0, 5)
                time.sleep(sleep_time)
                continue
            return html

        if response.status_code in (403, 429, 503):
            sleep_time = base_delay * (2 ** attempt) + random.uniform(0, 5)
            logging.warning(
                f"SourceForge returned {response.status_code} for {url}. "
                f"Sleeping {sleep_time:.2f}s before retry "
                f"(attempt {attempt + 1}/{max_retries})."
            )
            time.sleep(sleep_time)
            continue

        if response.status_code == 404:
            logging.warning(f"SourceForge returned 404 for {url}")
            return None

        logging.warning(f"Unexpected SourceForge status {response.status_code} for {url}")
        return None

    return None


# -------------------------------
# Web Scraping & Parsing
# -------------------------------

async def get_link_content(link):
    decoded_link = urllib.parse.unquote(link)

    if "galaxy.bi.uni-freiburg.de/tool_runner" in decoded_link:
        decoded_link = decoded_link.replace(
            "galaxy.bi.uni-freiburg.de/tool_runner",
            "usegalaxy.eu/root",
        )

    sourceforge_alternatives = [
        "sourceforge.net/projects/",
        "sf.net/p/",
        "sourceforge.net/p/",
    ]

    if any(alt in decoded_link for alt in sourceforge_alternatives):
        return fetch_sourceforge_html(decoded_link)

    return await extract_with_playwright(decoded_link)


def normalize_linebreaks(text: str) -> str:
    text = text.replace("\\n", "\n")
    text = text.replace("\r\n", "\n")
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract_main_text_from_html(html: str) -> str:
    doc = Document(html)
    summary_html = doc.summary()
    soup = BeautifulSoup(summary_html, "html.parser")

    for a in soup.find_all("a", href=True):
        text = a.get_text(strip=True)
        href = a["href"]
        if text:
            a.replace_with(f"[{text}]({href})")
        else:
            a.replace_with(f"<{href}>")

    for tag in soup.find_all(["strong", "b"]):
        text = tag.get_text(strip=True)
        tag.replace_with(f"**{text}**")

    for tag in soup.find_all(["em", "i"]):
        text = tag.get_text(strip=True)
        tag.replace_with(f"_{text}_")

    for i in range(1, 7):
        for header in soup.find_all(f"h{i}"):
            text = header.get_text(strip=True)
            header.replace_with(f"\n{'#' * i} {text}\n")

    for li in soup.find_all("li"):
        text = li.get_text(strip=True)
        li.replace_with(f"* {text}")

    for tag in soup(["script", "style", "footer", "nav"]):
        tag.decompose()

    text = soup.get_text(separator="\n", strip=True)
    text = normalize_linebreaks(text)

    with open("content_clean.html", "w", encoding="utf-8") as f:
        f.write(text)

    return text


def extract_sourceforge_project_info(html: str) -> dict:
    result = {
        "description": None,
        "sections": [],
    }

    try:
        soup = BeautifulSoup(html, "html.parser")

        desc_tag = soup.find("p", class_="description")
        if desc_tag:
            result["description"] = desc_tag.get_text(separator="\n", strip=True)

        for section in soup.find_all("div", class_="psp-section"):
            section_text = section.get_text(separator="\n", strip=True)
            links = [a["href"] for a in section.find_all("a", href=True)]

            inner_divs = section.find_all("div", recursive=False)
            for inner in inner_divs:
                section_text += "\n" + inner.get_text(separator="\n", strip=True)
                links.extend([a["href"] for a in inner.find_all("a", href=True)])

            result["sections"].append({
                "text": section_text.strip(),
                "hrefs": list(set(links)),
            })

        for section in soup.find_all("section", class_="psp-section"):
            section_text = section.get_text(separator="\n", strip=True)
            links = [a["href"] for a in section.find_all("a", href=True)]

            inner_divs = section.find_all("div", recursive=False)
            for inner in inner_divs:
                section_text += "\n" + inner.get_text(separator="\n", strip=True)
                links.extend([a["href"] for a in inner.find_all("a", href=True)])

            result["sections"].append({
                "text": section_text.strip(),
                "hrefs": list(set(links)),
            })

    except Exception as e:
        logging.warning(f"Error parsing SourceForge HTML: {e}")

    return result


def get_pypi_project_info(package_name):
    url = f"https://pypi.org/pypi/{package_name}/json"

    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()

        info = data.get("info", {})
        for key in list(info.keys()):
            if info[key] is None:
                del info[key]

        info["releases"] = list(data.get("releases", {}).keys())
        return info

    except Exception:
        return None


def get_bitbucket_metadata(user, repo):
    try:
        logging.info(f"Extracting metadata from Bitbucket repository {user}/{repo}")
        api_url = f"https://api.bitbucket.org/2.0/repositories/{user}/{repo}"
        response = requests.get(api_url, timeout=10)
        if response.status_code != 200:
            logging.warning(f"Failed to fetch metadata for {user}/{repo}: {response.status_code}")
            return {"error": f"Failed to fetch metadata: {response.status_code}"}
        return response.json()

    except Exception as e:
        return {"error": str(e)}


def get_bitbucket_readme(user, repo, metadata):
    try:
        main_branch = metadata.get("main_branch") or "master"
        readme_candidates = [
            "README.md", "README.rst", "README.txt",
            "readme.md", "readme.rst", "readme.txt",
        ]

        for filename in readme_candidates:
            raw_url = f"https://bitbucket.org/{user}/{repo}/raw/{main_branch}/{filename}"
            response = requests.get(raw_url, timeout=10)
            if response.status_code == 200 and response.text.strip():
                return response.text

        return None
    except Exception:
        return None


async def extract_with_playwright(url: str) -> str | None:
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                channel="chrome",
                args=[
                    "--proxy-bypass-list=<-loopback>",
                    "--dns-prefetch-disable",
                ],
            )

            context = await browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/118.0.5993.90 Safari/537.36"
                ),
                locale="en-US",
                viewport={"width": 1366, "height": 768},
            )

            page = await context.new_page()
            response = await page.goto(url, wait_until="networkidle", timeout=60000)
            await page.wait_for_timeout(8000)

            content = await page.content()
            final_url = page.url
            status = response.status if response else None

            logging.warning(f"Initial status for {url}: {status}")
            logging.warning(f"Final URL: {final_url}")

            with open("content.html", "w", encoding="utf-8") as f:
                f.write(content)

            await browser.close()

            if "Just a moment" in content or "Enable JavaScript and cookies to continue" in content:
                logging.warning(f"Cloudflare challenge not bypassed for {url}")
                return None

            return content

    except Exception as e:
        logging.warning(f"Playwright failed for {url}: {e}")
        return None


# -------------------------------
# Repository/Webpage Enrichment
# -------------------------------

def enrich_repo(url, clients: ExternalClients):
    repo = {"url": url, "metadata": None, "readme_content": None}
    try:
        parts = url.split("/")
        if len(parts) < 5:
            return repo
        owner, repo_name = parts[3], parts[4]
        logging.info(f"Fetching GitHub metadata for {owner}/{repo_name}")
        repo["repo_metadata"] = clients.github.get_repo_metadata(owner, repo_name)
        repo["readme_content"] = clients.github.get_repo_readme(owner, repo_name)
    except Exception as e:
        logging.error(f"Invalid GitHub URL: {url} -> {e}")

    return repo


def get_redirect(url):
    try:
        response = requests.head(url, allow_redirects=True, timeout=10)
        return response.url
    except Exception:
        return False


async def enrich_link(link, clients: ExternalClients):
    new_link = {"url": link}
    link = get_redirect(link)

    if link:
        processed = False

        if "github.com" in link:
            try:
                parts = link.split("/")
                if len(parts) >= 5:
                    owner, repo_name = parts[3], parts[4]
                    new_link["repo_metadata"] = clients.github.get_repo_metadata(owner, repo_name)
                    new_link["readme_content"] = clients.github.get_repo_readme(owner, repo_name)
                    processed = True
            except Exception as e:
                logging.warning(f"Error processing GitHub link {link}: {e}")
                raise e

        elif "gitlab.com" in link:
            metadata = clients.gitlab.get_project_metadata(link)
            new_link["repo_metadata"] = metadata

            if metadata:
                readme_url = metadata.get("readme_url")
                if readme_url:
                    new_link["readme_content"] = clients.gitlab.get_readme(readme_url, link)
                    processed = True

        elif "pypi.org/project/" in link:
            package_name = link.split("pypi.org/project/")[1].split("/")[0]
            metadata = get_pypi_project_info(package_name)
            new_link["project_metadata"] = metadata
            processed = True

        sourceforge_alternatives = [
            "sourceforge.net/projects/",
            "sf.net/p/",
            "sourceforge.net/p/",
        ]
        if any(alt in link for alt in sourceforge_alternatives):
            try:
                content = await get_link_content(link)
                if content:
                    project_info = extract_sourceforge_project_info(content)
                    new_link["project_metadata"] = project_info
                    processed = True
            except Exception as e:
                logging.warning(f"Error processing SourceForge link {link}: {e}")

        elif "bitbucket.org" in link:
            try:
                match = re.match(r"https?://bitbucket.org/([^/]+)/([^/]+)", link)
                user, repo = match.groups() if match else (None, None)
                metadata = get_bitbucket_metadata(user, repo)
                new_link["repo_metadata"] = metadata
                if metadata and "main_branch" in metadata:
                    new_link["readme_content"] = get_bitbucket_readme(user, repo, metadata)
                processed = True
            except Exception as e:
                logging.warning(f"Error processing Bitbucket link {link}: {e}")

        elif "git.bioconductor" in link:
            new_link["repo_metadata"] = {"url": link}
            processed = True

        if not processed:
            logging.info(f"Extracting generic content from {link}")
            content = await get_link_content(link)
            if content:
                text = extract_main_text_from_html(content)
                new_link["content"] = text

    return new_link