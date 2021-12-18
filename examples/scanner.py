import logging
import pprint

from flux_led.scanner import BulbScanner

logging.basicConfig(level=logging.DEBUG)

pprint.pprint(BulbScanner().scan(timeout=10))
