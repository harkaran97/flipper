from app.adapters.base import BaseSearchAdapter, SearchResult


class LinkUpStubAdapter(BaseSearchAdapter):
    async def web_search(self, query: str) -> SearchResult:
        return SearchResult(
            query=query,
            summary=(
                "Common fault found on this model. Typical repair costs range from "
                "£300 to £800 depending on severity. Independent garages in the UK "
                "typically charge £60-80/hour labour. Parts are widely available. "
                "This is a well-known issue covered in multiple forums and technical "
                "service bulletins."
            ),
            sources=[
                "https://www.honestjohn.co.uk/",
                "https://www.pistonheads.com/",
                "https://www.autocar.co.uk/",
            ],
        )
