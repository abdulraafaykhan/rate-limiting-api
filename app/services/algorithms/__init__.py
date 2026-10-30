"""Rate-limiting algorithms. Add a new one here to make it selectable."""

from app.services.algorithms.sliding_window_log import (
    SlidingWindowLogAlgorithm,
)
from app.services.algorithms.token_bucket import TokenBucketAlgorithm

# Algorithm name (as used in settings) -> the class that implements it.
ALGORITHM_CLASSES = {
    SlidingWindowLogAlgorithm.name: SlidingWindowLogAlgorithm,
    TokenBucketAlgorithm.name: TokenBucketAlgorithm,
}
