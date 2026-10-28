import os

os.environ["VD_NO_DOTENV"] = "1"  # a developer's local .env (API_TOKEN...) must not affect tests

import pytest  # noqa: E402

import app.main as m  # noqa: E402


@pytest.fixture(autouse=True)
def reset_limiter():
    # All test requests come from the same IP; don't let the per-minute limit spill over
    m.limiter.hits.clear()
