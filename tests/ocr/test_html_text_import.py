from pathlib import Path

from src.ocr.service import extract_text_from_file


def test_html_import_reads_visible_text_without_ocr(tmp_path: Path) -> None:
    path = tmp_path / "lesson.html"
    path.write_text(
        """
        <html>
          <head><style>.hidden { display:none; }</style><script>ignoreMe()</script></head>
          <body>
            <h1>Critical Thinking</h1>
            <p>Learn to <strong>cut through the noise</strong>.</p>
            <div>Challenge entrenched beliefs.</div>
          </body>
        </html>
        """,
        encoding="utf-8",
    )

    text = extract_text_from_file(path)

    assert "Critical Thinking" in text
    assert "cut through the noise" in text
    assert "entrenched beliefs" in text
    assert "ignoreMe" not in text
    assert "<strong>" not in text
