from gevent import monkey; monkey.patch_all()

import bottle
import click
import gevent
import logging
import sys
import time

from gevent.pool import Pool

from utils import log_exceptions, nice_shutdown
from utils.logging import configure_logging, wsgi_log_middleware

from github_tweeter import construct_app


CONTEXT_SETTINGS = {
    'help_option_names': ['-h', '--help']
}

log = logging.getLogger(__name__)

# Use an unbounded pool to track gevent greenlets so we can
# wait for them to finish on shutdown.
gevent_pool = Pool()


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
@click.option('--shutdown-sleep', default=10,
              help='How many seconds to sleep during graceful shutdown. (default=10)')
@click.option('--shutdown-wait', default=10,
              help='How many seconds to wait for active connections to close during graceful '
                   'shutdown (after sleeping). (default=10)')
@click.option('--json', '-j', default=False, is_flag=True,
              help='Log in json.')
@click.option('--verbose', '-v', default=False, is_flag=True,
              help='Log debug messages.')
@log_exceptions(exit_on_exception=True)
def main(**options):

    def shutdown():
        def wait():
            # Sleep for a few seconds to allow for race conditions between sending
            # the SIGTERM and load balancers stopping sending traffic here.
            log.info('Shutdown: Sleeping %(sleep_s)s seconds.',
                     {'sleep_s': options['shutdown_sleep']})
            time.sleep(options['shutdown_sleep'])

            log.info('Shutdown: Waiting up to %(wait_s)s seconds for connections to close.',
                     {'wait_s': options['shutdown_sleep']})
            gevent_pool.join(timeout=options['shutdown_wait'])

            log.info('Shutdown: Exiting.')
            sys.exit()

        # Run in greenlet, as we can't block in a signal hander.
        gevent.spawn(wait)

    configure_logging(json=options['json'], verbose=options['verbose'])

    app = construct_app(**options)
    app = wsgi_log_middleware(app)

    with nice_shutdown(shutdown):
        bottle.run(app,
                   host='0.0.0.0', port=options['port'],
                   server='gevent', spawn=gevent_pool,
                   # Disable default request logging - we're using middleware
                   quiet=True, error_log=None)


if __name__ == '__main__':
    main(auto_envvar_prefix='GITHUB_TWEETER_OPT')
