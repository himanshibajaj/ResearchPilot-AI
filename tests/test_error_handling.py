
from unittest.mock import patch

from src.main import search_web, run_research


def test_search_failure_returns_empty_list():
    with patch("src.main.DDGS") as mock_ddgs:
        mock_ddgs.return_value.text.side_effect = Exception(
            "Network unavailable"
        )

        result = search_web("test research question")

    assert result == []


def test_gemini_failure_is_handled():
    with patch("src.main.search_web", return_value=[]), \
         patch("src.main.collect_evidence", return_value=[]), \
         patch(
             "src.main.generate_report",
             side_effect=Exception("Gemini API unavailable")
         ), \
         patch("src.main.trace") as mock_trace, \
         patch("builtins.print") as mock_print:

        run_research("Explain enterprise AI applications")

    printed_output = " ".join(
        str(call.args[0])
        for call in mock_print.call_args_list
        if call.args
    )

    assert "Research failed" in printed_output
    assert "Exception" in printed_output

    logged_events = [
        call.args[0]
        for call in mock_trace.call_args_list
    ]

    assert "research_failed" in logged_events
