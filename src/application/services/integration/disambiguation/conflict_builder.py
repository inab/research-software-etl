from src.application.services.integration.disambiguation.prompts import get_tokenizer
from src.application.services.integration.disambiguation.enrich_links import enrich_link
# -------------------------------
# Chunking big text
# -------------------------------
def chunk_text(text: str, max_tokens: int = 8000, model: str = "gpt-4"):
    enc = get_tokenizer(model)
    words = text.split()
    chunks = []
    current_chunk = []
    current_token_count = 0

    for word in words:
        token_len = len(enc.encode(word + " "))
        if current_token_count + token_len > max_tokens:
            chunks.append(" ".join(current_chunk))
            current_chunk = [word]
            current_token_count = token_len
        else:
            current_chunk.append(word)
            current_token_count += token_len

    if current_chunk:
        chunks.append(" ".join(current_chunk))

    return chunks


# -------------------------------
# Conflict Handling
# -------------------------------

async def build_full_conflict(conflict, max_tokens=8000, model="gpt-4"):
    """
    Returns a conflict dictionary where:
    - 'disconnected' and 'remaining' contain minimal metadata (with URLs)
    - 'webpage_contents' and 'repository_contents' contain deduplicated content
    """

    async def enrich_and_collect_content(url_list):
        contents = {}
        seen = set()

        for url in url_list:
            if url in seen or not url:
                continue
            seen.add(url)

            enriched = await enrich_link(url)

            contents[url] = {}

            if enriched and enriched.get("content"):
                chunks = chunk_text(enriched["content"], max_tokens=max_tokens, model=model)
                contents[url]["Content"]  = chunks

            if enriched and enriched.get("readme_content"):
                contents[url]["README content"] = chunk_text(enriched.get("readme_content"), max_tokens=max_tokens, model=model)
            
            if enriched and enriched.get("repo_metadata"):
                contents[url]['Repository metadata'] = enriched["repo_metadata"]
            
            if enriched and enriched.get("project_metadata"):
                contents[url]["Project metadata"] = enriched["project_metadata"]

        return dict(contents)


    new_conflict = {
        "disconnected": [],
        "remaining": [],
        "webpage_contents": {},
    }

    all_webpages = set()
    all_repos = set()

    def strip_content_fields(entry):
        entry = entry.copy()
        webpages = entry.get("webpage", [])
        repos = entry.get("repository", [])
        all_webpages.update(webpages)
        for repo in repos:  
            if repo.get('kind') == "github" and "github.com" in repo.get('url', ''):
                all_repos.add(repo.get('url', ''))
            elif repo.get('kind') == "bitbucket" and "bitbucket.com" in repo.get('url', ''):
                all_repos.add(repo.get('url', ''))
            elif repo.get('kind') == "gitlab" and "gitlab.com" in repo.get('url', ''):
                all_repos.add(repo.get('url', ''))
            else:
                all_webpages.add(repo.get('url', ''))
            
        return entry

    for entry in conflict["disconnected"]:
        new_conflict["disconnected"].append(strip_content_fields(entry))

    for entry in conflict["remaining"]:
        new_conflict["remaining"].append(strip_content_fields(entry))

    # Enrich and chunk all unique URLs
    repos_and_webpages = all_webpages.union(all_repos)
    all_links = set(repos_and_webpages)
    new_conflict["webpage_contents"] = await enrich_and_collect_content(list(all_links))

    return new_conflict
