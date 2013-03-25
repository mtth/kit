#!/usr/bin/env python

from functools import partial
from requests import request as _request

def request(url, method='GET', only_json=True, **kwargs):
  resp = _request(method, 'http://nncsts.com:5000%s' % (url, ), **kwargs)
  try:
    json = resp.json()
  except:
    json = None
  if only_json:
    return json
  else:
    return (json, resp)

def get(url, method='GET', json=True):
  resp = _request(method, 'http://nncsts.com:5000%s' % (url, ))
  if json:
    if resp.status_code == 200:
      return resp.json()
    else:
      print 'error %s' % (resp.status_code, )
      return None
  else:
    return resp

