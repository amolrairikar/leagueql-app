from functools import partial

# Re-exported so existing ``from utils import correlation_id_var, logger,
# publish_failure`` imports in the processor package keep working.
from common.logging_utils import correlation_id_var, logger  # noqa: F401
from common.sns import publish_failure as _publish_failure

publish_failure = partial(_publish_failure, subject="LeagueQL Processor Failure")
