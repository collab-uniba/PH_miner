# PH_miner
A [ProductHunt.com](https://www.producthunt.com) miner in Python 3.

## Setup
1. Register your app using the [dashboard](https://www.producthunt.com/v1/oauth/applications).
2. In the root folder, create the file `credentials.yml` with the following structure:

```yaml
api:
  key: CLIENT_KEY
  secret: CLIENT_SECRET
  redirect_uri: APP_REDIRECT_URI
  dev_token: DEVELOPER_TOKEN
```

## Resources & Libraries
  * Product Hunt [API](https://api.producthunt.com/v1/docs)
  * [ph_py](https://github.com/anatg/ph_py) - ProductHunt.com API  wrapper in Python
