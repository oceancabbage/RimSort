import logging
from threading import Thread
from time import sleep

from steamworks import STEAMWORKS

logger = logging.getLogger(__name__)


class SteamworksInterface:
    """
    A class object to handle our interactions with SteamworksPy

    https://github.com/philippj/SteamworksPy
    https://philippj.github.io/SteamworksPy/
    https://github.com/philippj/SteamworksPy/issues/62
    https://github.com/philippj/SteamworksPy/issues/75
    https://github.com/philippj/SteamworksPy/pull/76

    Thanks to Paladin for the example
    """

    def __init__(self):
        logger.info("SteamworksInterface initializing...")
        self.callback_received = False  # Signal used to end the _callbacks Thread
        self.steamworks = STEAMWORKS()
        self.steamworks.initialize()  # Init the Steamworks API
        # Point Steamworks API callback response to our functions
        self.steamworks.Workshop.SetItemSubscribedCallback(self._cb_subscription_action)
        self.steamworks.Workshop.SetItemUnsubscribedCallback(
            self._cb_subscription_action
        )
        # Start the thread
        logger.info("Starting thread...")
        self.steamworks_thread = self._daemon()
        self.steamworks_thread.start()

    def _callbacks(self):
        logger.info("Starting _callbacks")
        while (
            not self.steamworks.loaded()
        ):  # This should not execute as long as Steamworks API init went OK
            logger.info("Waiting for Steamworks...")
        else:
            logger.info("Steamworks loaded!")
        while not self.callback_received:
            logger.info("Running callbacks...")
            self.steamworks.run_callbacks()
            sleep(0.1)
        else:
            logger.info("Callback received. Ending thread...")

    def _cb_subscription_action(self, *args, **kwargs) -> None:
        """
        Executes upon Steamworks API callback response
        """
        logger.info(f"Subscription action: {args}, {kwargs}")
        logger.info(
            f"Result: {args[0].result} PublishedFileId: {args[0].publishedFileId}"
        )
        # Set flag so that _callbacks cease
        self.callback_received = True

    def _daemon(self) -> Thread:
        """
        Returns a Thread pointing to our _callbacks daemon
        """
        return Thread(target=self._callbacks, daemon=True)
