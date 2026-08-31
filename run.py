import os
import sys
import logging
from app import create_app

app = create_app()

if __name__ == "__main__":
    # Configure stdout logging so API calls and stack traces always appear in the terminal
    root_logger = logging.getLogger()
    if not root_logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
        handler.setFormatter(formatter)
        root_logger.addHandler(handler)
    root_logger.setLevel(logging.INFO)

    # Ensure werkzeug logs are visible
    logging.getLogger('werkzeug').setLevel(logging.INFO)

    # Control whether to use the Flask reloader via env var. Default to False so a single process
    # writes logs to the terminal (avoids reloader spawning background process which can hide logs).
    use_reloader = os.environ.get('FLASK_USE_RELOADER', '0') == '1'

    # Respect FLASK_DEBUG env var if set, otherwise default to False when reloader is disabled
    debug_env = os.environ.get('FLASK_DEBUG')
    if debug_env is not None:
        debug = debug_env.lower() in ('1', 'true', 'yes')
    else:
        debug = False

    host = os.environ.get('FLASK_RUN_HOST', '127.0.0.1')
    port = int(os.environ.get('FLASK_RUN_PORT', 5000))

    app.run(host=host, port=port, debug=debug, use_reloader=use_reloader)
