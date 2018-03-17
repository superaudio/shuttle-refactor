import logging
from . import config

class Log(object):
    
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = object.__new__(cls)
            cls._instance.init()
        return cls._instance
    
    def init(self):
        logging.basicConfig(level = logging.DEBUG,
            format='%(asctime)s %(levelname)s %(message)s',
            filename=config['log']['filename'],
            filemod='a'
            )

    @classmethod
    def info(self, str):
        logging.info(str)
    
    @classmethod
    def warn(self, str):
        logging.warning(str)

    @classmethod
    def error(self, str):
        logging.error(str)

