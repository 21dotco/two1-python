import re

import pytest
from click.testing import CliRunner

from two1.cli import main
from two1.commands.search import search_lib
from two1.tests import test_utils


# @pytest.fixture(scope="session", autouse=True)
# def prepare_wallet():
#     test_utils.setup_wallet()
#
#
# @pytest.mark.apitest
# def test_search():
#     """Confirm that we can get any search results at all.
#
#     https://github.com/mitsuhiko/click/blob/master/tests/test_basic.py#L31
#     """
#     runner = CliRunner()
#     result = runner.invoke(main, ['search'])
#     assert len(result.output) > 0
#
#
# @pytest.mark.apitest
# def test_silent_search():
#     """Confirm that we can run search silently
#     https://github.com/mitsuhiko/click/blob/master/tests/test_basic.py#L31
#     """
#     runner = CliRunner()
#     result = runner.invoke(main, ['search', '--silent'])
#     assert len(result.output) == 0
#
#
# @pytest.mark.apitest
# def test_search_as_function():
#     """Confirm that we can get search results when called as a library.
#     """
#     listings = search_lib("testquery")
#     assert len(listings) >= 0
#
#
# @pytest.mark.apitest
# def test_search_query():
#     """Confirm that basic filtering works during search.
#     """
#     query = "image"
#     runner = CliRunner()
#     result = runner.invoke(main, ['search', '--query', query])
#     lines = result.output.split("\n")
#     matchlines = [re.search(query, xx) for xx in lines]
#     nmatch = len(list(filter(None, matchlines)))
#     assert nmatch > 0
#     nheaderlines = 5  # tabulate adds 5 format lines
#     assert len(lines) - nmatch == nheaderlines
#     assert len(result.output) > 0
#
#
# @pytest.mark.apitest
# def test_search_query_as_function():
#     """Confirm that basic filtering works during search.
#     """
#     listings_full = search_lib(silent=True)
#     listings = search_lib(query="face", silent=True)
#     assert len(listings) < len(listings_full)
#
#
# @pytest.mark.apitest
# def test_search_order():
#     """Confirm that search results are being properly ordered.
#     """
#     listings1 = search_lib(query="face", order="description", silent=True)
#     listings2 = search_lib(query="face", order="method", silent=True)
#     assert len(listings1) == len(listings2)
#     assert str(listings1) != str(listings2)
#
#
# @pytest.mark.xfail
# def test_publish_then_search():
#     """Confirm that we can publish an endpoint, then find it in search.
#     """
#     raise NotImplementedError
