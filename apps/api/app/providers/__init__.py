from app.providers.article import ArticleProvider
from app.providers.base import ContentProvider, FetchResult
from app.providers.default import DefaultProvider
from app.providers.instagram import InstagramProvider
from app.providers.youtube import YouTubeProvider

_REGISTRY: list[ContentProvider] = [
    YouTubeProvider(),
    InstagramProvider(),
    ArticleProvider(),
    DefaultProvider(),
]


def get_provider(url: str) -> ContentProvider:
    for provider in _REGISTRY:
        if provider.matches(url):
            return provider
    return DefaultProvider()
