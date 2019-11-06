import hashlib
import hmac
import json
import logging
import requests
import simplejson

from bottle import Bottle, abort, request, response
from requests_oauthlib import OAuth1

log = logging.getLogger(__name__)


def json_default_error_handler(http_error):
    response.content_type = 'application/json'
    return json.dumps({'error': http_error.body}, separators=(',', ':'))


def construct_app(github_webhook_secret,
                  twitter_consumer_key, twitter_consumer_secret,
                  twitter_token_key, twitter_token_secret,
                  **kwargs):
    app = Bottle()
    app.default_error_handler = json_default_error_handler

    webhook_secret_bytes = github_webhook_secret.encode()

    oauth = OAuth1(client_key=twitter_consumer_key,
                   client_secret=twitter_consumer_secret,
                   resource_owner_key=twitter_token_key,
                   resource_owner_secret=twitter_token_secret)

    @app.get('/status')
    def status():
        return 'OK'

    @app.post('/webhook')
    def webhook_post():

        provided_sig = request.headers.get('x-hub-signature')
        if provided_sig is None or provided_sig[:5] != 'sha1=':
            abort(401)

        provided_hash = provided_sig[5:]

        computed_hash = hmac.new(webhook_secret_bytes,
                                 request.body.read(),
                                 hashlib.sha1).hexdigest()

        if not hmac.compare_digest(provided_hash, computed_hash):
            abort(401)

        if request.headers.get('Content-Type') != 'application/json':
            abort(415, 'Require "Content-Type: application/json"')

        try:
            event = request.json
        except simplejson.JSONDecodeError:
            abort(400, 'POST data is not valid JSON')

        if not isinstance(event, dict):
            abort(400, 'POST body must be a JSON object')

        event_type = request.headers.get('x-github-event')
        if event_type is None or event_type != 'release':
            log.warning('Received unknown event type `%(event_type)s`.',
                        {'event_type': event_type,
                         'full_payload': event})
            return

        event_action = event['action']

        release = event['release']
        release_version = release['tag_name']
        release_prerelease = release['prerelease']
        release_url = release['html_url']

        repository = event['repository']
        repository_name = repository['name']
        repository_full_name = repository['full_name']
        repository_private = repository['private']

        if repository_private:
            log.warning('Received event for private repository `%(repository)s`.',
                        {'repository': repository_full_name,
                         'full_payload': event})
            return

        log.info('Received `%(action)s` event for version `%(version)s` of `%(repository)s`.',
                 {'action': event_action,
                  'version': release_version,
                  'repository': repository_full_name,
                  'full_payload': event})

        if event_action != 'published':
            return

        assert not release['draft'], \
            f"Received a 'published' event for a draft release. {release_url}"

        tweet = 'Pre-release version' if release_prerelease else 'Version'
        tweet += f" {release_version} of {repository_name} is out now: {release_url}"

        r = requests.post('https://api.twitter.com/1.1/statuses/update.json',
                          data={'status': tweet},
                          auth=oauth)
        r.raise_for_status()

        r_json = r.json()
        tweet_id = r_json['id_str']

        log.info('Tweeted about release `%(version)s` of `%(repository)s`. Tweet ID: `%(tweet_id)s`',
                 {'version': release_version,
                  'repository': repository_full_name,
                  'tweet_id': tweet_id,
                  'full_response': r_json})

    return app
