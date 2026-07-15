import urllib.parse
import logging
import re
from readability import Document
from bs4 import BeautifulSoup
from infrastructure.external.clients import ExternalClients

SOURCEFORGE_ALTERNATIVES = [
    "sourceforge.net/projects/",
    "sf.net/p/",
    "sourceforge.net/p/",
]


# -------------------------------
# Web Scraping & Parsing
# -------------------------------

async def get_link_content(link, clients: ExternalClients):
    decoded_link = urllib.parse.unquote(link)

    if "galaxy.bi.uni-freiburg.de/tool_runner" in decoded_link:
        decoded_link = decoded_link.replace(
            "galaxy.bi.uni-freiburg.de/tool_runner",
            "usegalaxy.eu/root",
        )

    if any(alt in decoded_link for alt in SOURCEFORGE_ALTERNATIVES):
        return clients.sourceforge.fetch_html(decoded_link)

    return await clients.browser.fetch(decoded_link)


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


async def enrich_link(link, clients: ExternalClients):
    new_link = {"url": link}
    link = clients.url_checker.resolve_redirects(link)

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
            metadata = clients.pypi.get_project_info(package_name)
            new_link["project_metadata"] = metadata
            processed = True

        if any(alt in link for alt in SOURCEFORGE_ALTERNATIVES):
            try:
                content = await get_link_content(link, clients)
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
                metadata = clients.bitbucket.get_repo_metadata(user, repo)
                new_link["repo_metadata"] = metadata
                if metadata and "main_branch" in metadata:
                    new_link["readme_content"] = clients.bitbucket.get_readme(user, repo, metadata)
                processed = True
            except Exception as e:
                logging.warning(f"Error processing Bitbucket link {link}: {e}")

        elif "git.bioconductor" in link:
            new_link["repo_metadata"] = {"url": link}
            processed = True

        if not processed:
            logging.info(f"Extracting generic content from {link}")
            content = await get_link_content(link, clients)
            if content:
                text = extract_main_text_from_html(content)
                new_link["content"] = text

    return new_link
