"""Tests for the audience builder module."""

from __future__ import annotations

from ssr_service.audience_builder import parse_evidence


class TestParseEvidence:
    """Tests for the multi-format parser."""

    def test_parse_csv(self):
        """Test CSV parsing and summarization."""
        csv_content = """name,age,income,region
Alice,25,High,US
Bob,34,Middle,UK
Carol,45,Low,US"""

        result = parse_evidence([("test.csv", csv_content)])

        assert "[test.csv]" in result
        assert "CSV with 3 rows" in result
        assert "name" in result
        assert "Alice" in result or "Bob" in result

    def test_parse_json_array(self):
        """Test JSON array parsing."""
        json_content = '[{"name": "Alice"}, {"name": "Bob"}]'

        result = parse_evidence([("data.json", json_content)])

        assert "[data.json]" in result
        assert "JSON array with 2 items" in result

    def test_parse_json_object(self):
        """Test JSON object parsing."""
        json_content = '{"demographics": {"age": "25-34"}, "sample_size": 100}'

        result = parse_evidence([("survey.json", json_content)])

        assert "[survey.json]" in result
        assert "demographics" in result

    def test_parse_text(self):
        """Test plain text parsing."""
        text_content = "This is a focus group summary about our target audience."

        result = parse_evidence([("notes.txt", text_content)])

        assert "[notes.txt]" in result
        assert "focus group" in result

    def test_parse_multiple_files(self):
        """Test parsing multiple files at once."""
        files = [
            ("data.csv", "col1,col2\na,b\nc,d"),
            ("notes.txt", "Some text notes here."),
        ]

        result = parse_evidence(files)

        assert "[data.csv]" in result
        assert "[notes.txt]" in result
        assert "---" in result  # Separator between files

    def test_parse_bytes_content(self):
        """Test that bytes content is handled correctly."""
        text_bytes = b"This is text as bytes."

        result = parse_evidence([("file.txt", text_bytes)])

        assert "text as bytes" in result

    def test_empty_csv(self):
        """Test handling of empty CSV."""
        result = parse_evidence([("empty.csv", "")])

        assert "Empty CSV" in result or "Failed to parse" in result

    def test_malformed_json(self):
        """Test handling of malformed JSON."""
        result = parse_evidence([("bad.json", "not valid json {")])

        assert "Failed to parse JSON" in result
