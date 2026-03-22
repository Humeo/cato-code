"""Tests for context_retriever — issue-aware code search."""
import pytest
from catocode.context_retriever import (
    extract_code_hints,
    build_code_context,
    CodeContext,
)


class TestExtractCodeHints:
    def test_extracts_file_paths(self):
        issue_text = "The bug is in src/auth/login.py line 42"
        hints = extract_code_hints(issue_text)
        assert "src/auth/login.py" in hints.file_paths

    def test_extracts_function_names_from_backticks(self):
        issue_text = "Calling `validate_token()` throws an error"
        hints = extract_code_hints(issue_text)
        assert "validate_token" in hints.symbol_names

    def test_extracts_class_names(self):
        issue_text = "The `AuthManager` class doesn't handle None"
        hints = extract_code_hints(issue_text)
        assert "AuthManager" in hints.symbol_names

    def test_extracts_from_stack_trace(self):
        issue_text = '''Traceback:
  File "src/handler.py", line 55, in process_request
    result = validate(data)
  File "src/validator.py", line 12, in validate
    raise ValueError("bad input")
'''
        hints = extract_code_hints(issue_text)
        assert "src/handler.py" in hints.file_paths
        assert "src/validator.py" in hints.file_paths
        assert "process_request" in hints.symbol_names
        assert "validate" in hints.symbol_names

    def test_extracts_error_type(self):
        issue_text = "Getting a ValueError when calling process()"
        hints = extract_code_hints(issue_text)
        assert "ValueError" in hints.error_types


class TestBuildCodeContext:
    @pytest.fixture
    def mock_store(self):
        from unittest.mock import MagicMock
        store = MagicMock()
        store.search_code_definitions.return_value = [
            {
                "file_path": "src/auth.py",
                "symbol_type": "function",
                "symbol_name": "validate_token",
                "signature": "def validate_token(token: str) -> bool",
                "body_preview": "def validate_token(token: str) -> bool:\n    ...",
                "line_start": 10,
                "line_end": 20,
                "language": "python",
                "children": None,
            }
        ]
        store.get_code_definitions.return_value = [
            {
                "file_path": "src/auth.py",
                "symbol_type": "function",
                "symbol_name": "validate_token",
                "signature": "def validate_token(token: str) -> bool",
                "body_preview": "def validate_token(token: str) -> bool:\n    ...",
                "line_start": 10,
                "line_end": 20,
                "language": "python",
                "children": None,
            }
        ]
        return store

    def test_build_code_context_from_issue(self, mock_store):
        issue_text = "The `validate_token` function fails on empty strings"
        ctx = build_code_context(
            repo_id="owner-repo",
            issue_text=issue_text,
            store=mock_store,
        )
        assert isinstance(ctx, CodeContext)
        assert len(ctx.relevant_definitions) > 0
        assert ctx.relevant_definitions[0]["symbol_name"] == "validate_token"

    def test_build_code_context_formats_to_markdown(self, mock_store):
        issue_text = "The `validate_token` function fails"
        ctx = build_code_context(
            repo_id="owner-repo",
            issue_text=issue_text,
            store=mock_store,
        )
        md = ctx.to_markdown()
        assert "validate_token" in md
        assert "src/auth.py" in md

    def test_build_code_context_empty_when_no_index(self):
        from unittest.mock import MagicMock
        store = MagicMock()
        store.search_code_definitions.return_value = []
        store.get_code_definitions.return_value = []
        store.get_code_index_state.return_value = None

        ctx = build_code_context("owner-repo", "some issue", store)
        assert ctx.relevant_definitions == []
        md = ctx.to_markdown()
        assert md == ""
