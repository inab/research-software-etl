# Integration tests for downloading content 
from src.application.services.integration.disambiguation.enrich_links import get_link_content 
import pytest 


pytestmark = pytest.mark.integration


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "url",
    [
        "https://sourceforge.net/projects/quasr",
        "https://sourceforge.net/projects/rtrm"
    ],
)
async def test_get_link_content_sourceforge_returns_content(url):
    result = await get_link_content(url)

    assert result is not None
    assert isinstance(result, str)
    assert result.strip() != ""

