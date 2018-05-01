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

5. Enable execution via crontab:
```bash
$ crontab -e
```
Add the following lines. Make sure to enter the correct path.
```bash
SHELL=bash
# New products are uploaded at 12.01 PST (just past midnight, 10am next morning in CET timezone):
# minute hour day-of-month month day-of-week command
    30     9       *          *       *        /path/.../to/PH_miner/run.sh /var/log/ph_miner.log 2>&1
```
6. Enable the rotation of the log file:
```bash
$ sudo ln -s ph_miner.logrotate /etc/logrotate.d/ph_miner
```

## Resources & Libraries
  * Product Hunt [API](https://api.producthunt.com/v1/docs)
  * [ph_py](https://github.com/anatg/ph_py) - ProductHunt.com API wrapper in Python
  * [Scrapy](https://scrapy.org) - A scraping and web-crawling framework
