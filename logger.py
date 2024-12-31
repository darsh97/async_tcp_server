import logging


class Logger:
    _instance = None

    """Logging Singleton Class"""

    def __new__(cls):
        if cls._instance is None:
            # Create a new instance of the logger
            cls._instance = logging.getLogger(__name__)
            cls._instance.setLevel(logging.DEBUG)  # Set global log level

            # Create console handler for logging
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.DEBUG)

            # Create a formatter for log messages
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            console_handler.setFormatter(formatter)

            # Add the handler to the logger
            cls._instance.addHandler(console_handler)

        return cls._instance


logger = Logger()
