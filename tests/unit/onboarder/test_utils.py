import json
import logging
from unittest.mock import patch

import pytest

from onboarder.utils import JsonFormatter, process_api_results, setup_logger


class TestJsonFormatter:
    def test_format_returns_valid_json_with_expected_fields(self):
        formatter = JsonFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="hello world",
            args=(),
            exc_info=None,
        )
        record.funcName = "my_function"

        with patch("onboarder.utils.time.time", return_value=1000.0):
            result = formatter.format(record)

        parsed = json.loads(result)
        assert parsed["timestamp"] == 1000000
        assert parsed["level"] == "INFO"
        assert parsed["message"] == "hello world"
        assert parsed["function"] == "my_function"


class TestSetupLogger:
    def test_returns_logger_with_correct_configuration(self):
        result = setup_logger()
        assert isinstance(result, logging.Logger)
        assert result.level == logging.INFO
        assert len(result.handlers) == 1
        assert isinstance(result.handlers[0], logging.StreamHandler)
        assert isinstance(result.handlers[0].formatter, JsonFormatter)


class TestProcessApiResults:
    def test_empty_results_returns_empty_list(self):
        assert process_api_results([]) == []

    def test_base_exception_raises_runtime_error(self):
        with pytest.raises(RuntimeError, match="Unexpected error occurred"):
            process_api_results([Exception("network error")])

    def test_data_none_raises_runtime_error(self):
        result = {"season": "2023", "data_type": "league_information", "data": None}
        with pytest.raises(RuntimeError, match="Failed to get data"):
            process_api_results([result])

    def test_valid_result_is_returned(self):
        result = {"season": "2023", "data_type": "league_information", "data": {}}
        assert process_api_results([result]) == [result]

    def test_multiple_valid_results_all_returned(self):
        results = [
            {"season": "2023", "data_type": "league_information", "data": {}},
            {"season": "2022", "data_type": "settings", "data": {"x": 1}},
        ]
        assert process_api_results(results) == results
