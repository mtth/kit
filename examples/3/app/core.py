#!/usr/bin/env python

from flasker import Flasker

fk_config = {
    'project_root': 'app',
    'db_url': 'sqlite:///app/db/db.sqlite',
    'logging_folder': 'logs',
    'oauth_credentials': {
      'google_client': '727771047328-orosiiaun16cf0p6q8sfal3dema77hq4.apps.googleusercontent.com',
      'google_secret': '6wSk04wHCNDma257YMzZbvqr'
    },
  }

fk = Flasker('Example 3', **fk_config)
