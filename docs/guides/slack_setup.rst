.. image:: https://img.shields.io/badge/-GitHub-181717.svg?logo=github&style=flat
   :target: https://github.com/kAIto47802/NotifyState
   :alt: GitHub
   :class: github-badge

Slack Bot Setup
===============

Before using NotifyState's SlackNotifier, you must create and configure a Slack app:

1. **Create a new Slack App**

   Go to https://api.slack.com/apps and click "Create New App" → "From scratch".
   Give it a name (e.g., "NotifyState") and select your workspace.

2. **Add Bot Token Scopes**

   In the left sidebar, choose "OAuth & Permissions" → "Scopes" → "Bot Token Scopes", and add ``chat:write``.

3. **Install the App to Your Workspace**

   In the left sidebar, choose "OAuth & Permissions" → "OAuth Tokens", and click "Install to <Your Workspace>", then "Allow".
   Copy the "Bot User OAuth Token" (starts with ``xoxb-...``).

4. **Invite the Bot to Your Channel**

   In Slack, go to the target channel and type:

   .. code-block:: bash

      /invite @NotifyState

.. warning::
   This procedure was verified on June 08, 2025. For the most up-to-date instructions, please refer to the `official Slack documentation <https://api.slack.com/quickstart>`__.
