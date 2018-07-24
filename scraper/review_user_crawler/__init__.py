import os

try:
    _ = os.environ['DB_CONFIG']
except KeyError:
    os.environ['DB_CONFIG'] = '../../db/cfg/dbsetup.yml'

try:
    _ = os.environ['PH_CREDENTIALS']
    pass
except KeyError:
    os.environ['PH_CREDENTIALS'] = '../../credentials_updater.yml'
