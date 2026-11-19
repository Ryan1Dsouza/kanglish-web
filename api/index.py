"""Vercel Python function entrypoint; all API access passes through cloud auth."""
from scripts.cloud.api import CloudHandler

class handler(CloudHandler):
    pass
