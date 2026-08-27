# tests/test_deliver.py
"""Webhook delivery, rate limits, and retry budget."""

from unittest.mock import MagicMock, patch

from calendarr.deliver import DISCORD_SUCCESS, send_payloads


def response(status: int, headers: dict | None = None, body: dict | None = None) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status
    resp.headers = headers or {}
    resp.json.return_value = body or {}
    resp.text = str(body or "")
    return resp


class TestSendPayloads:
    def test_success(self):
        with patch("calendarr.deliver.requests.post", return_value=response(204)) as post:
            assert send_payloads("http://hook", [{"content": "hi"}], DISCORD_SUCCESS, 30) is True
        assert post.call_count == 1

    def test_rate_limit_honors_retry_after(self):
        responses = [response(429, headers={"Retry-After": "2.5"}), response(204)]
        with (
            patch("calendarr.deliver.requests.post", side_effect=responses) as post,
            patch("calendarr.deliver.time.sleep") as sleep,
        ):
            assert send_payloads("http://hook", [{"content": "hi"}], DISCORD_SUCCESS, 30) is True
        assert post.call_count == 2
        sleep.assert_called_once_with(2.5)

    def test_negative_retry_after_clamped(self):
        responses = [response(429, headers={"Retry-After": "-5"}), response(204)]
        with (
            patch("calendarr.deliver.requests.post", side_effect=responses),
            patch("calendarr.deliver.time.sleep") as sleep,
        ):
            assert send_payloads("http://hook", [{"content": "hi"}], DISCORD_SUCCESS, 30) is True
        sleep.assert_called_once_with(0.0)

    def test_server_error_retries(self):
        responses = [response(502), response(204)]
        with (
            patch("calendarr.deliver.requests.post", side_effect=responses) as post,
            patch("calendarr.deliver.time.sleep"),
        ):
            assert send_payloads("http://hook", [{"content": "hi"}], DISCORD_SUCCESS, 30) is True
        assert post.call_count == 2

    def test_client_error_fails_immediately(self):
        with patch("calendarr.deliver.requests.post", return_value=response(400, body={"message": "bad"})) as post:
            assert send_payloads("http://hook", [{"content": "hi"}], DISCORD_SUCCESS, 30) is False
        assert post.call_count == 1

    def test_stops_after_first_failed_payload(self):
        with patch("calendarr.deliver.requests.post", return_value=response(400)) as post:
            payloads = [{"content": "a"}, {"content": "b"}]
            assert send_payloads("http://hook", payloads, DISCORD_SUCCESS, 30) is False
        assert post.call_count == 1
