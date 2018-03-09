import os

import yaml
from ph_py import ProductHuntClient
from ph_py.error import ProductHuntError

config_file = 'credentials.yml'


def run(key, secret, uri, token):
    phc = ProductHuntClient(key, secret, uri, token)

    # Example request
    try:
        for post in phc.get_todays_posts():
            print(post.name)
    except ProductHuntError as e:
        print(e.error_message)
        print(e.status_code)


if __name__ == '__main__':
    with open(os.path.join(os.getcwd(), config_file), 'r') as config:
        cfg = yaml.load(config)
        client_key = cfg['api']['key']
        client_secret = cfg['api']['secret']
        redirect_uri = cfg['api']['redirect_uri']
        dev_token = cfg['api']['dev_token']

    run(client_key, client_secret, redirect_uri, dev_token)
