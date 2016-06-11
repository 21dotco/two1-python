# Pull requests

## Code style

> Programs must be written for people to read, and only incidentally for machines to execute.
>
> -- Harold Abelson, Structure and Interpretation of Computer Programs

At a minimum, changes to the code should be compliant with [PEP 8](https://www.python.org/dev/peps/pep-0008/). For general design principles, consult [The Zen of Python](https://www.python.org/dev/peps/pep-0020/).

## Commit message format

Commit your changes using the following commit message format (with the same capitalization, spacing, and punctuation):

```
logging: Move function to module level
```

The first part of the message is the scope and the second part is a description of the change, written in the imperative tense.

## Commit history

Commits should be organized into logical units. Keep your git history clean by [rewriting](https://git-scm.com/book/en/v2/Git-Tools-Rewriting-History) it as necessary using `git rebase -i` (interactive rebase) and `git push -f` (force push). Commits addressing review comments and test failures should be squashed if necessary.

## Tests

Our test suite is automatically run on each commit of each pull request.

Add or modify tests as necessary, and run tests locally using [pytest](http://pytest.org/)

```shell
$ py.test
```

# Opening issues

## Bug reports

Bug reports should include clear instructions to reproduce the bug. Include a stack trace if applicable using the `--debug` flag:

```shell
21 --debug status
```

## Security issues

Critical security bugs should be sent via email to security@21.co and should not be publicly disclosed. Eligible security disclosures are eligible, at our sole discretion, for a monetary bounty of up to $1000 based on severity.
