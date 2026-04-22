import unittest

from theface.listing import (
    extract_article_authors,
    is_exclusive_author_credit,
    listing_url,
)


class ExtractArticleAuthorsTests(unittest.TestCase):
    def test_listing_url_uses_supplied_contributor_base(self) -> None:
        self.assertEqual(
            listing_url(1, contributor_base="https://theface.com/contributors/jade-wickes"),
            "https://theface.com/contributors/jade-wickes",
        )
        self.assertEqual(
            listing_url(3, contributor_base="https://theface.com/contributors/jade-wickes"),
            "https://theface.com/contributors/jade-wickes/p3",
        )

    def test_uses_visible_words_credit_not_meta_authors(self) -> None:
        html = """
        <html>
          <head>
            <meta name="parsely-author" content="Olive Pometsey" />
            <meta name="parsely-author" content="Jade Wickes" />
          </head>
          <body>
            <p class="tw-leading-none">
              <span class="contributors">
                <span class="contributors__type">Words: </span>
                <a class="contributors__name" href="/contributors/olive-pometsey">
                  Olive Pometsey
                </a>
              </span>
            </p>
          </body>
        </html>
        """

        authors = extract_article_authors(html)

        self.assertEqual(authors, ["Olive Pometsey"])
        self.assertTrue(is_exclusive_author_credit(authors))

    def test_keeps_all_names_listed_in_words_credit(self) -> None:
        html = """
        <html>
          <body>
            <p class="tw-leading-none">
              <span class="contributors">
                <span class="contributors__type">Words: </span>
                <a class="contributors__name" href="/contributors/olive-pometsey">
                  Olive Pometsey
                </a>,
                <a class="contributors__name" href="/contributors/jade-wickes">
                  Jade Wickes
                </a>,
                <a class="contributors__name" href="/contributors/davy-reed">
                  Davy Reed
                </a>
              </span>
              <time datetime="2024-09-02">2nd September 2024</time>
            </p>
          </body>
        </html>
        """

        authors = extract_article_authors(html)

        self.assertEqual(authors, ["Olive Pometsey", "Jade Wickes", "Davy Reed"])
        self.assertFalse(is_exclusive_author_credit(authors))

    def test_ignores_non_words_contributor_roles(self) -> None:
        html = """
        <html>
          <head>
            <meta name="parsely-author" content="Olive Pometsey" />
          </head>
          <body>
            <p class="tw-leading-none">
              <span class="contributors">
                <span class="contributors__type">Photography: </span>
                <a class="contributors__name" href="/contributors/jordan-margolin">
                  Jordan Margolin
                </a>
              </span>
            </p>
          </body>
        </html>
        """

        self.assertEqual(extract_article_authors(html), [])


if __name__ == "__main__":
    unittest.main()
