import logging


def configure_logging() -> None:
    """
    Configure app logging to be visible when running under uvicorn.

    Uvicorn installs its own logging config; calling basicConfig() alone may be a no-op
    if handlers already exist. This function ensures our `src.*` loggers are INFO and
    propagate to root handlers, while keeping uvicorn logs intact.
    """
    fmt = "%(asctime)s %(levelname)s [%(name)s] %(message)s"
    root = logging.getLogger()
    if not root.handlers:
        logging.basicConfig(level=logging.INFO, format=fmt)
    else:
        root.setLevel(logging.INFO)

    # Ensure application loggers are visible
    app_logger = logging.getLogger("src")
    app_logger.setLevel(logging.INFO)
    app_logger.propagate = True

    # Keep uvicorn loggers at INFO as well
    logging.getLogger("uvicorn.error").setLevel(logging.INFO)
    logging.getLogger("uvicorn.access").setLevel(logging.INFO)
