# coding: utf-8
"""Tests for the LiteLLM provider module.
Run standalone: python -m pytest test/test_litellm_provider.py -v --override-ini='pythonpath=.'
"""
import sys
import types
import unittest
from unittest import TestCase, mock
from unittest.mock import MagicMock, patch

# Stub heavy deps that break on Python 3.12 before any test imports
_null_mod = types.ModuleType("null")
_null_mod.Null = type("Null", (), {})
sys.modules.setdefault("null", _null_mod)


def _mock_response(content="Test summary", role="assistant"):
    resp = MagicMock()
    resp.model_dump.return_value = {
        "choices": [{"message": {"role": role, "content": content}, "finish_reason": "stop"}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
    }
    return resp


def _empty_response():
    resp = MagicMock()
    resp.model_dump.return_value = {"choices": [{"message": {"role": "assistant", "content": None}}]}
    return resp


def _no_choices_response():
    resp = MagicMock()
    resp.model_dump.return_value = {"choices": []}
    return resp


class LiteLLMProviderTestCase(TestCase):

    def setUp(self):
        import config
        config.litellm_model = "openai/gpt-4o-mini"
        config.litellm_api_key = ""

    def test_basic_summarize(self):
        import litellm
        with patch.object(litellm, "completion", return_value=_mock_response("Scientists discovered a new particle.")):
            from hacker_news.llm.litellm import summarize_by_litellm
            result = summarize_by_litellm("Some long article about physics...")
            self.assertIn("particle", result)
            litellm.completion.assert_called_once()
            call_kwargs = litellm.completion.call_args[1]
            self.assertEqual(call_kwargs["model"], "openai/gpt-4o-mini")

    def test_translate_system_prompt(self):
        import litellm
        with patch.object(litellm, "completion", return_value=_mock_response("Translated text")):
            from hacker_news.llm.litellm import translate_by_litellm
            translate_by_litellm("Some text", "simplified Chinese")
            sys_msg = litellm.completion.call_args[1]["messages"][0]
            self.assertIn("simplified Chinese", sys_msg["content"])

    def test_drop_params_always_true(self):
        import litellm
        with patch.object(litellm, "completion", return_value=_mock_response("ok")):
            from hacker_news.llm.litellm import call_litellm
            call_litellm("content", "system prompt")
            self.assertTrue(litellm.completion.call_args[1]["drop_params"])

    def test_api_key_forwarded(self):
        import config
        config.litellm_api_key = "sk-test-key"
        import litellm
        with patch.object(litellm, "completion", return_value=_mock_response("ok")):
            from hacker_news.llm.litellm import call_litellm
            call_litellm("content", "prompt")
            self.assertEqual(litellm.completion.call_args[1]["api_key"], "sk-test-key")

    def test_api_key_omitted_when_empty(self):
        import litellm
        with patch.object(litellm, "completion", return_value=_mock_response("ok")):
            from hacker_news.llm.litellm import call_litellm
            call_litellm("content", "prompt")
            self.assertNotIn("api_key", litellm.completion.call_args[1])

    def test_empty_content_returns_empty(self):
        import litellm
        with patch.object(litellm, "completion", return_value=_empty_response()):
            from hacker_news.llm.litellm import call_litellm
            self.assertEqual(call_litellm("content", "prompt"), "")

    def test_no_choices_returns_empty(self):
        import litellm
        with patch.object(litellm, "completion", return_value=_no_choices_response()):
            from hacker_news.llm.litellm import call_litellm
            self.assertEqual(call_litellm("content", "prompt"), "")

    def test_think_tags_stripped(self):
        import litellm
        with patch.object(litellm, "completion", return_value=_mock_response("<think>reasoning</think>The actual summary.")):
            from hacker_news.llm.litellm import call_litellm
            result = call_litellm("content", "prompt")
            self.assertNotIn("think", result)
            self.assertIn("actual summary", result)

    def test_auth_error_raises(self):
        import litellm
        with patch.object(litellm, "completion",
                          side_effect=litellm.AuthenticationError(message="Invalid key", model="test", llm_provider="openai")):
            from hacker_news.llm.litellm import call_litellm
            with self.assertRaises(litellm.AuthenticationError):
                call_litellm("content", "prompt")

    def test_rate_limit_raises(self):
        import litellm
        with patch.object(litellm, "completion",
                          side_effect=litellm.RateLimitError(message="Rate limited", model="test", llm_provider="openai")):
            from hacker_news.llm.litellm import call_litellm
            with self.assertRaises(litellm.RateLimitError):
                call_litellm("content", "prompt")

    def test_timeout_raises(self):
        import litellm
        with patch.object(litellm, "completion",
                          side_effect=litellm.Timeout(message="Timed out", model="test", llm_provider="openai")):
            from hacker_news.llm.litellm import call_litellm
            with self.assertRaises(litellm.Timeout):
                call_litellm("content", "prompt")

    def test_missing_model_raises(self):
        import config
        config.litellm_model = ""
        from hacker_news.llm.litellm import call_litellm
        with self.assertRaises(ValueError):
            call_litellm("content", "prompt")

    def test_markdown_stripped(self):
        import litellm
        with patch.object(litellm, "completion", return_value=_mock_response("**Bold** summary.")):
            from hacker_news.llm.litellm import call_litellm
            result = call_litellm("content", "prompt")
            self.assertNotIn("**", result)


if __name__ == '__main__':
    unittest.main()
