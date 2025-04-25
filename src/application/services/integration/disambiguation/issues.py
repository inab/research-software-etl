import requests
import json
import os
from jinja2 import Environment, FileSystemLoader

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")

def create_issue(issue):
    with open('data/issues.json', 'a') as f:
        f.write(json.dumps(issue, indent=4))

def generate_github_issue(context, template_path='template.md'):
    env = Environment(loader=FileSystemLoader('.'))
    template = env.get_template(template_path)
    return template.render(context)

def extract_url(repo):
    return repo.get("url") if isinstance(repo, dict) else repo

def prepare_description(description_list):
    if not description_list:
        return "No description available."

    if isinstance(description_list, str):
        return description_list.strip()

    if isinstance(description_list, list):
        # Strip whitespace and remove empty descriptions
        cleaned = [desc.strip() for desc in description_list if desc.strip()]
        if not cleaned:
            return "No description available."
        return "\n\n".join(cleaned)

    return str(description_list)  # Fallback, just in case

def prepare_publications(publications):
    if not publications:
        return "No publications listed."

    formatted = []
    for pub in publications:
        parts = []

        title = pub.get("title")
        year = pub.get("year")
        if title:
            parts.append(f"**{title}**")
        if year:
            parts[-1] += f" ({year})"

        # Prefer URL, then DOI, then identifiers
        link = pub.get("url") or (f"https://doi.org/{pub['doi']}" if pub.get("doi") else None)
        if link:
            parts.append(f"[Link]({link})")

        # Add optional identifiers if they exist
        ids = []
        if pub.get("doi"):
            ids.append(f"DOI: {pub['doi']}")
        if pub.get("pmid"):
            ids.append(f"PMID: {pub['pmid']}")
        if pub.get("pmcid"):
            ids.append(f"PMCID: {pub['pmcid']}")

        if ids:
            parts.append(", ".join(ids))

        formatted.append(" – ".join(parts))

    return "\n\n".join(formatted)


def prepare_license(license_data):
    if not license_data:
        return "No license information."

    value = license_data.get("value", "").strip()
    url = license_data.get("url", "").strip()

    if value and url:
        return f"[{value}]({url})"
    elif value:
        return value
    elif url:
        return f"[License link]({url})"
    else:
        return "No license information."

def prepare_documentation(docs):
    if not docs:
        return "No documentation available."

    lines = []
    for doc in docs:
        doc_type = doc.get("type", "Unknown").capitalize()
        url = doc.get("url")
        if url:
            lines.append(f"- [{doc_type}]({url})")
        else:
            lines.append(f"- {doc_type} (no URL)")

    return "\n".join(lines)


def prepare_authors(authors):
    if not authors:
        return "No authors listed."

    formatted = []
    for author in authors:
        author_type = author.get("type", "Unknown")
        name = author.get("name", "Unnamed")
        email = author.get("email")

        if email:
            formatted.append(f"{name} ({author_type}, [{email}](mailto:{email}))")
        else:
            formatted.append(f"{name} ({author_type})")

    return "\n".join(formatted)

def preprocess_entry(entry):
    data = entry["data"]
    return {
        "id": entry.get("id"),
        "name": data.get("name"),
        "source": data.get("source")[0],
        "version": data.get("version"),
        "type": data.get("type"),
        "repository": extract_url(data.get("repository")),
        "website": data.get("website"),
        "authors": prepare_authors(data.get("authors")),
        "publications": prepare_publications(data.get("publications")),
        "license": prepare_license(data.get("license")),
        "description": prepare_description(data.get("description")),
        "documentation": prepare_documentation(data.get("documentation")),   
    }

def generate_context(key, full_conflict):
    return {
        "id": key,
        "entry_a": preprocess_entry(full_conflict["disconnected"][0]),
        "entry_b": preprocess_entry(full_conflict["remaining"][0])
    }


def create_github_issue(title, body, labels=None):
    """
    Create a GitHub issue.

    Args:
        title (str): Issue title.
        body (str): Markdown body (pre-rendered).
        token (str): GitHub personal access token.
        labels (list[str], optional): List of labels.

    Returns:
        dict: The GitHub API response as a dict.
    """
    url = f"https://api.github.com/repos/inab/research-software-etl/issues"
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json"
    }

    payload = {
        "title": title,
        "body": body
    }

    if labels:
        payload["labels"] = labels

    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()  # raise if request failed
    return response.json()