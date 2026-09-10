import json
import logging


class JsonFormatter(logging.Formatter):
    def format(self, record):
        return json.dumps({'level': record.levelname, 'component': record.name,
                           'message': record.getMessage()})


def configure(debug=False):
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    logging.basicConfig(level=logging.DEBUG if debug else logging.WARNING, handlers=[handler], force=True)
