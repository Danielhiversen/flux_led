import logging

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

        return _retry_wrap

    return decorator_retry
