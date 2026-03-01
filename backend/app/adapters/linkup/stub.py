from app.adapters.base import BaseSearchAdapter, SearchResult

PARTS_STUB_RESULTS = {
    "timing chain kit": [
        {"supplier": "GSF Car Parts", "price_pence": 8700,
         "url": "https://www.gsf.co.uk/timing-chain-kit", "in_stock": True},
        {"supplier": "Euro Car Parts", "price_pence": 9400,
         "url": "https://www.eurocarparts.com/timing-chain-kit", "in_stock": True},
        {"supplier": "The Parts People", "price_pence": 8200,
         "url": "https://thepartspeople.co.uk/timing-chain-kit", "in_stock": True},
    ],
    "engine oil": [
        {"supplier": "GSF Car Parts", "price_pence": 2200,
         "url": "https://www.gsf.co.uk/engine-oil", "in_stock": True},
        {"supplier": "Euro Car Parts", "price_pence": 2400,
         "url": "https://www.eurocarparts.com/engine-oil", "in_stock": True},
    ],
}

PARTS_STUB_DEFAULT = [
    {"supplier": "GSF Car Parts", "price_pence": 5000,
     "url": "https://www.gsf.co.uk/parts", "in_stock": True},
]


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
