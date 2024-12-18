from enum import Enum


class PublicationState(Enum):
    DRAFT = "DRAFT"
    PENDING_APPROVAL = "PENDING"
    PUBLISHED = "PUBLISHED"
    DISCARDED = "DISCARDED"


YOUTUBE_POOL_COLLECTION = "youtube-pool"
