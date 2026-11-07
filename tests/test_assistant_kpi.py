import pytest
from src.assistant.kpi import _scenario, answer_data


def test_allowed_scenario():
    assert _scenario('original') == 'original'


def test_reject_scenario():
    with pytest.raises(ValueError):
        _scenario('original; DROP TABLE dw.fact_orders')


def test_reject_unknown_intent():
    with pytest.raises(ValueError):
        answer_data('execute_sql')
