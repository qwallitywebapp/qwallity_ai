import logging
import sys

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)]
    )

    for name in ("gunicorn.error", "gunicorn.access"):
        lg = logging.getLogger(name)
        lg.handlers = logging.getLogger().handlers
        lg.setLevel(logging.INFO)
    