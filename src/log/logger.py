import logging

server_logger = logging.getLogger("server")
if not server_logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter("[%(levelname)s] %(asctime)s - %(name)s - %(message)s")
    handler.setFormatter(formatter)
    server_logger.addHandler(handler)
server_logger.setLevel(logging.INFO)

db_logger = logging.getLogger("db")
if not db_logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter("[%(levelname)s] %(asctime)s - %(name)s - %(message)s")
    handler.setFormatter(formatter)
    db_logger.addHandler(handler)
db_logger.setLevel(logging.INFO)

crawl_logger = logging.getLogger("crawler")
if not crawl_logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter("[%(levelname)s] %(asctime)s - %(name)s - %(message)s")
    handler.setFormatter(formatter)
    crawl_logger.addHandler(handler)
crawl_logger.setLevel(logging.INFO)