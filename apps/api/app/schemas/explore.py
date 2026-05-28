from pydantic import BaseModel


class ExploreStats(BaseModel):
    total_items: int
    public_collections: int
    weekly_new: int
