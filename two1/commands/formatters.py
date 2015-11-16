"""Formatters for custom two1 buys."""

import json
from textwrap import wrap
from tabulate import tabulate


def search_formatter(res, maxresults=4):
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


def sms_formatter(res):
    """custom formatter for SMS messages."""
    data = res.json()
    return 'The following SMS is queued to be sent to: {} \nMessage: "{}"\n'.format(
        data["to"],
        data["body"],
        data["from"]
    )
