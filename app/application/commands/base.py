from typing import Protocol, TypeVar


class Command(Protocol):
    """Marker protocol for state-changing application requests."""


CommandT = TypeVar("CommandT", bound=Command, contravariant=True)
ResultT = TypeVar("ResultT", covariant=True)


class CommandHandler(Protocol[CommandT, ResultT]):
    async def handle(self, command: CommandT) -> ResultT:
        """Handle a command and return an application-specific result."""
