# PH_miner
A [ProductHunt.com](https://www.producthunt.com) miner in Python 3.

## Installation
```bash
$ git clone https://github.com/collab-uniba/PH_miner.git
$ git submodule init
$ git submodule update
```

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

3. Create the folder `db/cfg/`, then create therein the file `dbsetup.yml` to setup the connection to the MySQL database:
```yaml
mysql:
    host: 127.0.0.1
    user: root
    passwd: *******
    db: producthunt
```

4. Install packages via pip:
```bash
$ pip install -r requirements.txt
```

## Resources & Libraries
  * Product Hunt [API](https://api.producthunt.com/v1/docs)
  * [ph_py](https://github.com/anatg/ph_py) - ProductHunt.com API wrapper in Python
  * [Scrapy](https://scrapy.org) - A scraping and web-crawling framework
