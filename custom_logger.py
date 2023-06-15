import logging
import queue
from logging.handlers import QueueHandler, QueueListener, TimedRotatingFileHandler


log_queue = queue.Queue()
queue_handler = QueueHandler(log_queue)

FORMATTER = logging.Formatter(
    "%(asctime)s.%(msecs)03d - %(levelname)s - %(name)s: %(funcName)s:%(lineno)d - %(message)s",
    datefmt="%d-%b-%y %H:%M:%S",
)
LOG_FILE = "app.log"


def get_file_handler():
    file_handler = TimedRotatingFileHandler(LOG_FILE, when="midnight", backupCount=5)
    file_handler.setFormatter(FORMATTER)
    return file_handler


def get_logger(logger_name):
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.DEBUG)
    logger.addHandler(queue_handler)
    logger.propagate = False
    listener = QueueListener(log_queue, get_file_handler())
    return (logger, listener)
