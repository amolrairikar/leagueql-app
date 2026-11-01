"""Shared AWS client configuration.

Vendored into every function's deployment zip. Centralizes the botocore retry
policy so each module's ``boto3`` client uses the same settings.
"""

import botocore.config

RETRY_CONFIG = botocore.config.Config(retries={"mode": "standard"})
