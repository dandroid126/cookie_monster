import signal
import threading
from typing import Optional

from src.constants import LOGGER

TAG = "signal_util"


class SignalUtil:
    """
    Utility class for handling signals such as SIGINT and SIGTERM.
    """
    is_interrupted = False
    condition = threading.Condition()

    def __init__(self, cleanup_timeout: Optional[float] = None):
        """
        Initialize the SignalUtil
        """

        self.cleanup_timeout = cleanup_timeout

        self.original_sigint_handler = signal.getsignal(signal.SIGINT)
        self.original_sigterm_handler = signal.getsignal(signal.SIGTERM)

        # Register the interrupt function for SIGINT and SIGTERM
        signal.signal(signal.SIGINT, self.interrupt)
        signal.signal(signal.SIGTERM, self.interrupt)

    def interrupt(self, *args):
        """
        Handle interruptions of the program to release resources and exit gracefully

        Args:
            *args: The arguments.

        Returns:
            None
        """
        self.is_interrupted = True
        LOGGER.i(TAG, f"interrupt(): interrupted. args: {args}")
        self.condition.acquire()
        self.condition.notify_all()
        self.condition.release()

        # Give the program time to clean up
        if self.cleanup_timeout is not None:
            LOGGER.i(TAG, f"interrupt(): waiting so the program can clean up.")
            self.wait(self.cleanup_timeout)

        # Restore the original signal handlers and repeat the signal
        signal.signal(signal.SIGINT, self.original_sigint_handler)
        signal.signal(signal.SIGTERM, self.original_sigterm_handler)
        signal.raise_signal(args[0])

    def wait(self, timeout: Optional[float]):
        """
        Wait function that allows for the program to gracefully exit if interrupted. Use this function in the main loop instead of time.sleep().

        Args:
            timeout: The amount of time to wait in seconds

        Returns:

        """
        self.condition.acquire()
        self.condition.wait(timeout)
        self.condition.release()


# Initialize the SignalUtil instance to be used globally
signal_util = SignalUtil(1)
