.. image:: https://img.shields.io/badge/-GitHub-181717.svg?logo=github&style=flat
   :target: https://github.com/kAIto47802/NotifyState
   :alt: GitHub
   :class: github-badge

Quickstart
==========

Get up and running with NotifyState in just a few steps!

Installation
------------

Install the latest release from our `GitHub <https://github.com/kAIto47802/NotifyState>`__:

.. code-block:: bash

   pip install git+https://github.com/kAIto47802/NotifyState.git


Set Up Your Notifier (e.g., Slack or Discord)
---------------------------------------------

Currently, Slack and Discord are supported.
For setup instructions, please refer to the :doc:`guides` section.


Basic Usage
-----------

For more detailed usage, please refer to the :doc:`api` sections.


Watch a Function or Block of Code
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Wrap any function or block with the :func:`~notifystate._core.watch` function to get automatic start/stop/error alerts:

**Use as a decorator to monitor a function**:

.. code-block:: python

   import notifystate

   @notifystate.watch(send_to="slack")
   def long_task():
       # This function will be monitored
       # Your long-running code here
       ...

**Or use as a context manager to monitor a block of code**:

.. code-block:: python

   import notifystate

   with notifystate.watch(send_to="slack"):
       # Code inside this block will be monitored
       # Your long-running code here
       ...


Send a One-Off Notification
^^^^^^^^^^^^^^^^^^^^^^^^^^^

You can also send notifications with the :func:`~notifystate._core.send` function at any point in your code, not just at the start or end of a task:

.. code-block:: python

   import notifystate

   # Immediately send "Job finished!" to your Slack channel
   notifystate.send("Job finished!", send_to="slack")

   # You can also send any Python data (it will be stringified)
   notifystate.send(data, send_to="slack")


Configuring Defaults
^^^^^^^^^^^^^^^^^^^^

Rather than specifying ``send_to`` and other options every time, you can initialize once with the :func:`~notifystate._core.init` function:

.. code-block:: python

   import notifystate

   # Set up Slack notifiers with defaults
   notifystate.init(send_to="slack", channel="my-channel", mention_to="@U012345678")

   # Now you only need to call send or watch without repeating options
   notifystate.send("All systems go!")

   with notifystate.watch():
       # This will use the defaults set in init
       ...

Environment Variables
^^^^^^^^^^^^^^^^^^^^^

You can also configure default channels and tokens via environment variables, so you don't have to pass ``channel`` or ``token`` every time:

.. code-block:: bash

   # For Slack notifier
   export SLACK_CHANNEL="my-channel"
   export SLACK_BOT_TOKEN="xoxb-1234..."

   # For Discord notifier
   export DISCORD_CHANNEL="1234567890"
   export DISCORD_BOT_TOKEN="ABCD1234..."

Once set, you can omit those parameters:

.. code-block:: python

   import notifystate

   # Will use SLACK_CHANNEL and SLACK_BOT_TOKEN
   notifystate.init(send_to="slack")

   notifystate.send("Automatic notification!")

   with notifystate.watch():
       ...


.. note::
   The channel and token must be set, either via environment variables or as function arguments.
   If not set, the notification will not be sent, and an error will be logged
   (the original Python script will continue running without interruption).

Custom Notifier Instances
^^^^^^^^^^^^^^^^^^^^^^^^^

Instead of the procedural API, you can also create a notifier instance and call its methods:

.. code-block:: python

   from notifystate import SlackNotifier

   # Create a SlackNotifier with defaults
   slack = SlackNotifier(
       channel="my-channel",
       mention_to="@U012345678",  # Mention a specific user (Optional)
   )

   # Send a one-off message
   slack.send("Hello via instance!")

   # Or watch a function:
   @slack.watch()
   def long_task():
       # Your long-running code here
       ...

Next Steps
----------

- Explore the :doc:`api` for full customization options.