"""Formatters for custom two1 buys."""

import json
from textwrap import wrap
from tabulate import tabulate


def search_formatter(res, maxresults=10):
    """custom formatter for search."""
    formatted_search_results = []
    headers = ("No.", "Result")
    search_results = json.loads(res.json()['results'])['d']['results']
    for i, search_result in enumerate(search_results):
        if i < maxresults:
            title = search_result["Title"]
            url = search_result["Url"]
            desc = search_result["Description"]

            formatted_search_results.append([i, title])
            formatted_search_results.append(["", "-----------------"])
            formatted_search_results.append(["", url])
            for k, l in enumerate(wrap(desc, 80)):
                formatted_search_results.append(["", l])
            formatted_search_results.append(["", ""])
    return(
        tabulate(
            formatted_search_results,
            headers=headers,
            tablefmt="psql"
            )
        )


def social_formatter(res):
    """custom formatter for social."""
    data = res.json()["success"]
    return 'The following Twitter DM was recieved by: @{}\n"{}"\n'.format(
        data["recipient_screen_name"],
        data["text"]
    )


def content_formatter(res):
    """custom formatter for content."""
    url = res.json()["article"]
    return "You just purchased the article {}".format(url)


def text_formatter(res):
    """custom formatter for text messages."""
    data = res.json()
    return 'The following SMS is queued to be sent to: {} \n"{}" from: {}\n'.format(
        data["to"],
        data["body"],
        data['from']
    )
