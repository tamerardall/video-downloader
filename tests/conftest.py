import pytest

import app.main as m


@pytest.fixture(autouse=True)
def reset_limiter():
    # Testler aynı IP'den gelir; dakikalık sınır testler arasında taşmasın
    m.limiter.hits.clear()
