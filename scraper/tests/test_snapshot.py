import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import MagicMock, patch

from theface import snapshot


@contextmanager
def _fake_open_page(**kwargs):
    yield MagicMock()


class SnapshotResumeTests(unittest.TestCase):
    def test_partition_existing_outputs_splits_existing_and_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            out_dir = Path(tmpdir)
            out_dir.mkdir(parents=True, exist_ok=True)
            (out_dir / "first-article.png").write_bytes(b"existing")

            existing, missing = snapshot.partition_existing_outputs(
                [
                    "https://theface.com/culture/first-article",
                    "https://theface.com/culture/second-article",
                ],
                out_dir,
                suffix=".png",
            )

            self.assertEqual(existing, ["https://theface.com/culture/first-article"])
            self.assertEqual(missing, ["https://theface.com/culture/second-article"])

    def test_take_screenshots_skips_existing_png(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            out_dir = Path(tmpdir)
            target = out_dir / "example-article.png"
            out_dir.mkdir(parents=True, exist_ok=True)
            target.write_bytes(b"existing")
            progress = []

            with patch("theface.snapshot._open_page", _fake_open_page), patch(
                "theface.snapshot._goto_with_fallback"
            ) as goto_mock, patch(
                "theface.snapshot._capture_stitched_screenshot"
            ) as capture_mock:
                snapshot.take_screenshots(
                    ["https://theface.com/culture/example-article"],
                    out_dir,
                    progress=lambda url, path: progress.append((url, path)),
                )

            goto_mock.assert_not_called()
            capture_mock.assert_not_called()
            self.assertEqual(
                progress,
                [("https://theface.com/culture/example-article", target)],
            )

    def test_take_screenshots_continues_after_failed_url(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            out_dir = Path(tmpdir)
            progress = []
            warnings = []

            def _goto(page, url):
                if url.endswith("first-article"):
                    raise RuntimeError("network changed")

            with patch("theface.snapshot._open_page", _fake_open_page), patch(
                "theface.snapshot._goto_with_fallback",
                side_effect=_goto,
            ), patch(
                "theface.snapshot._capture_stitched_screenshot"
            ) as capture_mock:
                failures = snapshot.take_screenshots(
                    [
                        "https://theface.com/culture/first-article",
                        "https://theface.com/culture/second-article",
                    ],
                    out_dir,
                    progress=lambda url, path: progress.append((url, path.name)),
                    warning=lambda url, path, exc: warnings.append((url, str(exc))),
                )

            self.assertEqual(len(failures), 1)
            self.assertEqual(failures[0]["url"], "https://theface.com/culture/first-article")
            self.assertEqual(
                progress,
                [
                    ("https://theface.com/culture/first-article", "first-article.png"),
                    ("https://theface.com/culture/second-article", "second-article.png"),
                ],
            )
            self.assertEqual(
                warnings,
                [("https://theface.com/culture/first-article", "network changed")],
            )
            capture_mock.assert_called_once()

    def test_render_pdfs_skips_existing_pdf(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            out_dir = Path(tmpdir)
            target = out_dir / "example-article.pdf"
            out_dir.mkdir(parents=True, exist_ok=True)
            target.write_bytes(b"existing")
            progress = []

            with patch("theface.snapshot._open_page", _fake_open_page), patch(
                "theface.snapshot._goto_with_fallback"
            ) as goto_mock, patch(
                "theface.snapshot._capture_stitched_image"
            ) as capture_mock, patch(
                "theface.snapshot._save_paginated_pdf"
            ) as save_mock:
                snapshot.render_pdfs(
                    ["https://theface.com/culture/example-article"],
                    out_dir,
                    progress=lambda url, path: progress.append((url, path)),
                )

            goto_mock.assert_not_called()
            capture_mock.assert_not_called()
            save_mock.assert_not_called()
            self.assertEqual(
                progress,
                [("https://theface.com/culture/example-article", target)],
            )

    def test_render_pdfs_continues_after_failed_url(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            out_dir = Path(tmpdir)
            progress = []
            warnings = []

            def _goto(page, url):
                if url.endswith("first-article"):
                    raise RuntimeError("navigation timeout")

            with patch("theface.snapshot._open_page", _fake_open_page), patch(
                "theface.snapshot._goto_with_fallback",
                side_effect=_goto,
            ), patch(
                "theface.snapshot._capture_stitched_image",
                return_value=object(),
            ), patch(
                "theface.snapshot._save_paginated_pdf"
            ) as save_mock:
                failures = snapshot.render_pdfs(
                    [
                        "https://theface.com/culture/first-article",
                        "https://theface.com/culture/second-article",
                    ],
                    out_dir,
                    progress=lambda url, path: progress.append((url, path.name)),
                    warning=lambda url, path, exc: warnings.append((url, str(exc))),
                )

            self.assertEqual(len(failures), 1)
            self.assertEqual(failures[0]["url"], "https://theface.com/culture/first-article")
            self.assertEqual(
                progress,
                [
                    ("https://theface.com/culture/first-article", "first-article.pdf"),
                    ("https://theface.com/culture/second-article", "second-article.pdf"),
                ],
            )
            self.assertEqual(
                warnings,
                [("https://theface.com/culture/first-article", "navigation timeout")],
            )
            save_mock.assert_called_once()


if __name__ == "__main__":
    unittest.main()
