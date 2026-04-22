import argparse
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import scrape


def _args(output_dir: Path) -> argparse.Namespace:
    return argparse.Namespace(
        output_dir=output_dir,
        start_page=1,
        max_pages=15,
        delay=1.5,
        author_name=None,
        contributor_slug=None,
    )


class DiscoverUrlsTests(unittest.TestCase):
    def test_parser_accepts_common_flags_after_subcommand(self) -> None:
        args = scrape.build_parser().parse_args(
            [
                "discover",
                "--author-name",
                "Jade Wickes",
                "--contributor-slug",
                "jade-wickes",
                "--author-name",
                "Craig McLean",
                "--contributor-slug",
                "craig-mclean",
            ]
        )

        self.assertEqual(args.command, "discover")
        self.assertEqual(args.author_name, ["Jade Wickes", "Craig McLean"])
        self.assertEqual(args.contributor_slug, ["jade-wickes", "craig-mclean"])

    def test_build_targets_preserves_order_and_uses_author_subdirs_for_multi(self) -> None:
        args = _args(Path("/tmp/theface-output"))
        args.author_name = ["Jade Wickes", "Davy Reed"]
        args.contributor_slug = ["jade-wickes", "davy-reed"]

        targets = scrape._build_targets(args)

        self.assertEqual([target.author_name for target in targets], args.author_name)
        self.assertEqual(
            [target.contributor_slug for target in targets],
            ["jade-wickes", "davy-reed"],
        )
        self.assertEqual(
            [target.output_dir for target in targets],
            [
                Path("/tmp/theface-output/jade-wickes"),
                Path("/tmp/theface-output/davy-reed"),
            ],
        )

    def test_build_targets_uses_explicit_slug_override(self) -> None:
        args = _args(Path("/tmp/theface-output"))
        args.author_name = ["Jade Wickes"]
        args.contributor_slug = ["custom-slug"]

        targets = scrape._build_targets(args)

        self.assertEqual(targets[0].contributor_slug, "custom-slug")
        self.assertEqual(targets[0].output_dir, Path("/tmp/theface-output/custom-slug"))

    def test_build_targets_puts_default_olive_output_in_slug_subdir(self) -> None:
        targets = scrape._build_targets(_args(Path("/tmp/theface-output")))

        self.assertEqual(targets[0].author_name, scrape.EXPECTED_AUTHOR)
        self.assertEqual(
            targets[0].output_dir,
            Path("/tmp/theface-output/olive-pometsey"),
        )

    def test_build_targets_requires_slug_when_author_is_given(self) -> None:
        args = _args(Path("/tmp/theface-output"))
        args.author_name = ["Jade Wickes"]

        with self.assertRaises(ValueError):
            scrape._build_targets(args)

    def test_write_url_index_stores_plain_url_list(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            index_path = Path(tmpdir) / "article_urls.json"

            scrape._write_url_index(index_path, ["https://theface.com/music/example"])

            payload = json.loads(index_path.read_text(encoding="utf-8"))
            self.assertEqual(payload, ["https://theface.com/music/example"])

    def test_load_url_index_reads_plain_url_list(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            index_path = Path(tmpdir) / "article_urls.json"
            index_path.write_text(
                json.dumps(["https://theface.com/music/example"]),
                encoding="utf-8",
            )

            urls = scrape._load_url_index(index_path)

            self.assertEqual(urls, ["https://theface.com/music/example"])

    def test_discover_urls_overwrites_existing_index(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            index_path = output_dir / "article_urls.json"
            index_path.write_text(
                json.dumps(["https://theface.com/music/stale-example"]),
                encoding="utf-8",
            )
            fresh_urls = [
                "https://theface.com/music/fresh-one",
                "https://theface.com/music/fresh-two",
            ]
            candidate_urls = [
                "https://theface.com/music/candidate-one",
                "https://theface.com/music/candidate-two",
                "https://theface.com/music/candidate-three",
            ]
            target = scrape.ContributorTarget(
                author_name="Jade Wickes",
                contributor_slug="jade-wickes",
                output_dir=output_dir,
            )
            page_bar = MagicMock()
            verify_bar = MagicMock()

            with patch(
                "scrape.collect_all_article_urls",
                return_value=candidate_urls,
            ) as collect_mock, patch(
                "scrape.filter_exclusive_article_urls",
                return_value=fresh_urls,
            ) as filter_mock, patch(
                "scrape.tqdm",
                side_effect=[page_bar, verify_bar],
            ):
                urls = scrape._discover_urls(
                    _args(output_dir),
                    session=object(),
                    target=target,
                )

            self.assertEqual(urls, fresh_urls)
            collect_mock.assert_called_once()
            filter_mock.assert_called_once()
            self.assertEqual(
                collect_mock.call_args.kwargs["contributor_base"],
                "https://theface.com/contributors/jade-wickes",
            )
            self.assertEqual(
                filter_mock.call_args.kwargs["expected_author"],
                "Jade Wickes",
            )
            payload = json.loads(index_path.read_text(encoding="utf-8"))
            self.assertEqual(payload, fresh_urls)
            page_bar.close.assert_called_once()
            verify_bar.close.assert_called_once()

    def test_load_saved_urls_requires_existing_index(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            target = scrape.ContributorTarget(
                author_name="Jade Wickes",
                contributor_slug="jade-wickes",
                output_dir=output_dir,
            )

            with self.assertRaises(FileNotFoundError):
                scrape._load_saved_urls(target)


if __name__ == "__main__":
    unittest.main()
