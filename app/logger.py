import logging
from logging.handlers import RotatingFileHandler
import os

class Logger(object):


    @staticmethod
    def getAppHandler():
        Logger.createLogDirectoryIfNotPresent()
        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        handler = RotatingFileHandler('logs/out.log', maxBytes=10000, backupCount=1)
        handler.setFormatter(formatter)
        handler.setLevel(logging.DEBUG)
        return handler

    @staticmethod
    def createLogDirectoryIfNotPresent():
        if not os.path.exists("logs/"):
            os.mkdir("logs/")
