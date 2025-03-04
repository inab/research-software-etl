import requests
from src.application.services.url_resolver import URLResolver

class RequestsURLResolver(URLResolver):
    def resolve(self, url: str) -> bool:
        try:
            response = requests.head(url, allow_redirects=True, timeout=5)
            return response.status_code < 400
        except requests.RequestException:
            return False

    def check_url_with_fallback(self, url: str, timeout: int = 5) -> bool:
        '''
        Checks if a URL resolves. Returns True if the URL resolves, else False.
        '''
        def try_url(protocol: str, base_url: str) -> bool:
            full_url = f"{protocol}://{base_url}" if not base_url.startswith((f"{protocol}://")) else base_url
            return self.resolve(full_url)

        # Check if protocol is already present; if not, assume https
        if "://" not in url:
            url = f"https://{url}"

        # Attempt with the original protocol (https by default)
        if try_url("https", url):
            return True

        # Fallback to http if https fails
        return try_url("http", url)