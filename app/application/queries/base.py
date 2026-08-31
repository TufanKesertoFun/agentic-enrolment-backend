from typing import Protocol, TypeVar


class Query(Protocol):
    """Marker protocol for read-only application requests."""


QueryT = TypeVar("QueryT", bound=Query, contravariant=True)
ResultT = TypeVar("ResultT", covariant=True)


class QueryHandler(Protocol[QueryT, ResultT]):
    async def handle(self, query: QueryT) -> ResultT:
        """Handle a query and return an application-specific result."""
