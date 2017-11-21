#!/usr/bin/python
import requests


class Error(Exception):
    pass


def fetch(url):
    try:
        resp = requests.request('GET', url)
    except requests.exceptions.InvalidSchema:
        raise Error('url must start with "http://"')
    except:
        raise
    return resp
