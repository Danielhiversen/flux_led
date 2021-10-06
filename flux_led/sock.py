import logging
import socket

_LOGGER = logging.getLogger(__name__)


def _socket_retry(attempts=2):
    """Define a wrapper to retry on socket failures."""

    def decorator_retry(func):
        def _retry_wrap(self, *args, retry=attempts, **kwargs) -> None:
            attempts_remaining = retry + 1
            while attempts_remaining:
                attempts_remaining -= 1
                try:
                    ret = func(self, *args, **kwargs)
                    self.set_available()
                    return ret
                except socket.error as ex:
                    _LOGGER.debug(
                        "%s: socket error while calling %s: %s", self.ipaddr, func, ex
                    )
            self.set_unavailable()

        return _retry_wrap

    return decorator_retry
