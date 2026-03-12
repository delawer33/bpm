import logging
import sys

from pythonjsonlogger import jsonlogger

logger = logging.getLogger("app_logger")
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler(sys.stdout)

formatter = jsonlogger.JsonFormatter(
    "%(asctime)s %(levelname)s %(name)s %(message)s %(request_id)s"
)
handler.setFormatter(formatter)
logger.addHandler(handler)


class RequestIDFilter(logging.Filter):
    def __init__(self, request_id="unknown"):
        super().__init__()
        self.request_id = request_id

    def filter(self, record):
        record.request_id = self.request_id
        return True
