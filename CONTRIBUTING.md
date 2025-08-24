# Contribution Guidelines

Contributions to this project are welcome!

Thank you for considering contributing to this project. Your contributions help improve the project and benefit the community.


## General Guidelines

- Make Pull Requests (PRs) from your own fork of the repository. The official documentation for [forking a repository](https://docs.github.com/en/get-started/quickstart/fork-a-repo) can help you with this, if you're not familiar with the process.
- Ensure your code adheres to the project's coding standards:
   - We use [ruff](https://docs.astral.sh/ruff/) for code formatting and linting.
   - We use [mypy](https://mypy.readthedocs.io/en/stable/) for type checking.
   - We use [pytest](https://docs.pytest.org/en/stable/) for testing.
- Include tests for any new features you implement.
- Update the documentation if your changes affect the usage of the library.
   - The documentation is located in the `docs` directory as well as in the docstrings of the code.
   - The documentation is written in [reStructuredText](https://www.sphinx-doc.org/en/master/usage/restructuredtext/index.html) format.
   - You can build the documentation locally. To do this, first install the required dependencies with `pip install '.[docs]'`, then run `make html` in the `docs` directory. The built documentation will be available in the `docs/_build/html` directory.

## Adding a New Notifier

If you need another platform that is not currently supported, feel free to open an issue or submit a pull request. We are always looking to expand the capabilities of this library.

To add a new notifier, please follow these steps:
1. Create a new Python file in the [`notist/_notifiers/`](https://github.com/kAIto47802/NotifyState/tree/main/notist/_notifiers) directory.
2. Implement the notifier class, subclassing the [`BaseNotifier`](https://github.com/kAIto47802/NotifyState/blob/main/notist/_notifiers/base.py) class found in [`notist/_notifiers/base.py`](https://github.com/kAIto47802/NotifyState/blob/main/notist/_notifiers/base.py).
   - Implement the [`_do_send`](https://github.com/kAIto47802/NotifyState/blob/main/notist/_notifiers/base.py#L244-L252) method according to each platform's API.
   - [`SlackNotifier`](https://github.com/kAIto47802/NotifyState/blob/main/notist/_notifiers/slack.py) and [`DiscordNotifier`](https://github.com/kAIto47802/NotifyState/blob/main/notist/_notifiers/discord.py) can serve as examples for how to implement the notifier class.
3. Add corresponding tests in the [`tests/notifiers_test`](https://github.com/kAIto47802/NotifyState/tree/main/tests/notifiers_test) directory to ensure the notifier works as expected.
4. Add corresponding documentation in the [`docs/api`](https://github.com/kAIto47802/NotifyState/tree/main/docs/api) directory to explain how to use the new notifier.
5. Add guides for setting up the notifier in the [`docs/guides`](https://github.com/kAIto47802/NotifyState/tree/main/docs/guides) directory.
