from jinja2 import Environment, FileSystemLoader
from datetime import datetime, timezone

from infrastructure.config import PipelineConfig


def generate_github_body(context, template_path=None):
    """Render the curator-facing issue body.

    The template is *read*, not written, so falling back to the packaged default is
    safe -- but callers in the pipeline pass the path from the config the CLI built.
    """
    template_path = template_path or PipelineConfig().github_issue_template_path
    env = Environment(loader=FileSystemLoader('.'))
    template = env.get_template(str(template_path))
    return template.render(context)

def extract_url(repo):
    urls = ""
    for repos in repo:
        if isinstance(repos, dict):
            url = repos.get("url")
            if url:
                urls += f"\n\t- {url}"
        elif isinstance(repos, str):
            urls += f"\n\t- {repos}"

    return urls

def prepare_website(websites):
    if not websites:
        return "No website available."

    if isinstance(websites, str):
        return f"\n\t- [{websites}]({websites})"

    if isinstance(websites, list):
        cleaned = [website.strip() for website in websites if website.strip()]
        if not cleaned:
            return "No website available."

        text = ""
        for item in cleaned:
            text += f"\n\t- [{item}]({item})"
        return text

    return str(websites)  # Fallback, just in case


def prepare_description(description_list):
    if not description_list:
        return "No description available."

    if isinstance(description_list, str):
        return f"\n\t```\n\t{description_list.strip()}\n\t```\n"

    if isinstance(description_list, list):
        # Strip whitespace and remove empty descriptions
        cleaned = [desc.strip() for desc in description_list if desc.strip()]
        if not cleaned:
            return "No description available."

        text = "\n\t```"    
        for item in cleaned:
            text += f"\n\t{item}"

        text += "\n\t```"
        return text
    
    
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
    licenses = ""
    if not license_data:
        return "No license information."
    
    for license in license_data:

        value = license.get("name", "")
        url = license.get("url", "")

        if value and url:
           licenses += f"\n\t- [{value}]({url})"
        elif value:
            licenses += f"\n\t- {value}"
        elif url:
            licenses += f"\n\t- [License link]({url})"
    else:
        return "No license information."

def prepare_documentation(docs):
    if not docs:
        return "No documentation available."

    text = ""
    for doc in docs:
        doc_type = doc.get("type", "Unknown").capitalize()
        url = doc.get("url")
        if url:
            text += f"\n\t- [{doc_type}]({url})"
        else:
            text += f"\n\t- {doc_type} (no URL)"

    return text


def prepare_authors(authors):
    if not authors:
        return "No authors listed."

    formatted = ""
    for author in authors:
        author_type = author.get("type", "Unknown")
        name = author.get("name", "Unnamed")
        email = author.get("email")

        if email:
            formatted += f"\n\t- {name} ({author_type}, [{email}](mailto:{email}))"
        else:
            formatted += (f"\n\t-{name} ({author_type})")

    return formatted

def preprocess_entry(entry):

    return {
        "id": entry.get("id"),
        "name": entry.get("name"),
        "source": entry.get("source")[0],
        "version": entry.get("version"),
        "type": entry.get("type"),
        "repository": extract_url(entry.get("repository")),
        "website": prepare_website(entry.get("webpage")),
        "authors": prepare_authors(entry.get("authors")),
        "publications": prepare_publications(entry.get("publications")),
        "license": prepare_license(entry.get("license")),
        "description": prepare_description(entry.get("description")),
        "documentation": prepare_documentation(entry.get("documentation")),   
    }

def generate_context(key, conflict_id, full_conflict, conflict_url, run_id):
    return {
        "name": key,
        "id": conflict_id,
        "entry_a": preprocess_entry(full_conflict["disconnected"][0]),
        "entry_b": preprocess_entry(full_conflict["remaining"][0]),
        'conflict_url': conflict_url,
        'run_id': run_id
    }




def generate_conflict_file(conflict, conflict_name, conflict_id, run_id):
    
    content = {
        'date': datetime.now(timezone.utc).isoformat(),
        'conflict_name': conflict_name,
        'conflict_id': conflict_id,
        'run_id': run_id,
        'conflict': conflict
    }

    filename = f"{conflict_id}.json"
    
    return content, filename
