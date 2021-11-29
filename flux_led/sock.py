import logging
from typing import TYPE_CHECKING, Any, Callable, TypeVar, cast

from .const import DEFAULT_RETRIES

_LOGGER = logging.getLogger(__name__)


WrapFuncType = TypeVar("WrapFuncType", bound=Callable[..., Any])


if TYPE_CHECKING:
    from .device import WifiLedBulb


def _socket_retry(attempts: int = DEFAULT_RETRIES) -> WrapFuncType:
    """Define a wrapper to retry on socket failures."""

    def decorator_retry(func: WrapFuncType) -> WrapFuncType:
        def _retry_wrap(
            self: "WifiLedBulb",
            *args: Any,
            retry: int = attempts,
            **kwargs: Any,
        ) -> Any:
            attempts_remaining = retry + 1
            while attempts_remaining:
                attempts_remaining -= 1
                try:
                    ret = func(self, *args, **kwargs)
                    self.set_available()
                    return ret
                except OSError as ex:
                    _LOGGER.debug(
                        "%s: socket error while calling %s: %s", self.ipaddr, func, ex
                    )
                    if attempts_remaining:
                        continue
                    self.set_unavailable()
                    self.close()
                    # We need to raise or the bulb will
                    # always be seen as available in Home Assistant
                    # when it goes offline
                    raise

        return cast(WrapFuncType, _retry_wrap)

    return cast(WrapFuncType, decorator_retry)
