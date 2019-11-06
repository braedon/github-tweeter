from gevent import monkey; monkey.patch_all()

import bottle
import click
import logging
import time

from gevent.pool import Pool

from github_tweeter import construct_app
from logging_utils import configure_logging, wsgi_log_middleware
from utils import log_exceptions, nice_shutdown, graceful_cleanup

CONTEXT_SETTINGS = {
    'help_option_names': ['-h', '--help']
}

log = logging.getLogger(__name__)

# Use an unbounded pool to track gevent greenlets so we can
# wait for them to finish on shutdown.
gevent_pool = Pool()


@log_exceptions(exit_on_exception=True)
@nice_shutdown()
@click.command(context_settings=CONTEXT_SETTINGS)
@click.option('--github-webhook-secret', required=True,
              help='Github webhook secret.')
@click.option('--twitter-consumer-key', required=True,
              help='Twitter consumer API key.')
@click.option('--twitter-consumer-secret', required=True,
              help='Twitter consumer API secret key.')
@click.option('--twitter-token-key', required=True,
              help='Twitter access token.')
@click.option('--twitter-token-secret', required=True,
              help='Twitter access token secret.')
@click.option('--port', '-p', default=8080,
              help='Port to serve API on (default=8080).')
@click.option('--json', '-j', default=False, is_flag=True,
              help='Log in json.')
@click.option('--verbose', '-v', default=False, is_flag=True,
              help='Log debug messages.')
def main(**options):

    def graceful_shutdown():
        log.info('Starting graceful shutdown.')
        # Sleep for a few seconds to allow for race conditions between sending
        # the SIGTERM and load balancers stopping sending traffic here and
        time.sleep(5)
        # Allow any running requests to complete before exiting.
        # Socket is still open, so assumes no new traffic is reaching us.
        gevent_pool.join()

    configure_logging(json=options['json'], verbose=options['verbose'])

    app = construct_app(**options)
    app = wsgi_log_middleware(app)

    with graceful_cleanup(graceful_shutdown):
        bottle.run(app,
                   host='0.0.0.0', port=options['port'],
                   server='gevent', spawn=gevent_pool,
                   # Disable default request logging - we're using middleware
                   quiet=True, error_log=None)


if __name__ == '__main__':
    main(auto_envvar_prefix='GITHUB_TWEETER_OPT')
