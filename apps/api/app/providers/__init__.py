from app.providers.article import ArticleProvider
from app.providers.base import ContentProvider, FetchResult
from app.providers.youtube import YouTubeProvider

_REGISTRY: list[ContentProvider] = [
    YouTubeProvider(),
    ArticleProvider(),
]


def get_provider(url: str) -> ContentProvider:
    for provider in _REGISTRY:
        if provider.matches(url):
            return provider
    return ArticleProvider()
