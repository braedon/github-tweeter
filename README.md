# Github Tweeter

A simple bot that listens to `release` type event webhooks from Github, and tweets about `published` releases.

## How To Deploy

### 1. Twitter Setup

To allow Github Tweeter to tweet as you, you'll need to create a Twitter app. This requires a Twitter developer account - I'll leave that as an exercise for the reader. Once you have a developer account, go to https://developer.twitter.com/en/apps and `Create an app`. Fill in all the required fields appropriately - all optional fields can be left blank - and `Create` the app.

Once created, go to the `Keys and tokens` tab of the app settings. Generate an access token, and then take note of the `Access token & access token secret`, and `Consumer API keys`. You'll need them to configure Github Tweeter in the next step.

### 2. Github Tweeter Deployment

Github Tweeter serves a REST endpoint at `/webhook` (on port `8080` by default), which needs to be deployed to a public URL (e.g. https://example.com/github-tweeter/webhook) on the hosting of your choice. This is the endpoint that Github will send event webhooks to.

You will need to configure Github Tweeter with the various keys and secrets from the Twitter app created in the previous step.

It also needs a shared secret that Github will use to sign the webhooks it sends. You can generate this however you like, but it should be long and random. Take note of it for the next step.

Github Tweeter can be run directly from source, though this isn't recommended for production deployments.

```
> pip3 install -r requirements.txt
> python3 main.py -h
Usage: main.py [OPTIONS]

Options:
  --github-webhook-secret TEXT    Github webhook secret.  [required]
  --twitter-consumer-key TEXT     Twitter consumer API key.  [required]
  --twitter-consumer-secret TEXT  Twitter consumer API secret key.  [required]
  --twitter-token-key TEXT        Twitter access token.  [required]
  --twitter-token-secret TEXT     Twitter access token secret.  [required]
  -p, --port INTEGER              Port to serve API on (default=8080).
  -j, --json                      Log in json.
  -v, --verbose                   Log debug messages.
  -h, --help                      Show this message and exit.
> python3 main.py \
    --github-webhook-secret <your-github-webhook-secret> \
    --twitter-consumer-key <your-twitter-consumer-key> \
    --twitter-consumer-secret <your-twitter-consumer-secret> \
    --twitter-token-key <your-twitter-token-key> \
    --twitter-token-secret <your-twitter-token-secret>
```

For production deployments, using the provided [docker image](https://hub.docker.com/repository/docker/braedon/github-tweeter) is recommended, as is using environment variables to provide the various keys and secrets.

```
> sudo docker run --rm --name github-tweeter \
    -e GITHUB_TWEETER_OPT_GITHUB_WEBHOOK_SECRET=<your-github-webhook-secret> \
    -e GITHUB_TWEETER_OPT_TWITTER_CONSUMER_KEY=<your-twitter-consumer-key> \
    -e GITHUB_TWEETER_OPT_TWITTER_CONSUMER_SECRET=<your-twitter-consumer-secret> \
    -e GITHUB_TWEETER_OPT_TWITTER_TOKEN_KEY=<your-twitter-token-key> \
    -e GITHUB_TWEETER_OPT_TWITTER_TOKEN_SECRET=<your-twitter-token-secret> \
    braedon/github-tweeter:<version>
```

### 3. Github Setup

To connect a Github repository, configure a webhook (`Settings` -> `Webhooks` -> `Add webhook`) with the following settings:

- **Payload URL:** https://example.com/github-tweeter/webhook
- **Content type:** `application/json`
- **Secret:** The Github webhook secret you generated earlier.
- **Which events would you like...:** Select `Let me select individual events.` and check `Releases`. Uncheck everything else.

Note that when you initially add a webhook Github will send a `ping` type event. If you've already deployed Github Tweeter, it will log a warning that it has received an unknown event type - this is safe to ignore.

### 4. Create a Release

Assuming everything is setup correctly, the next time you create a release - a full Github release, not a git tag - Github Tweeter will post a tweet from your account announcing the release, and linking to the release on Github.
