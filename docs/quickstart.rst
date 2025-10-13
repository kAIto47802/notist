Quickstart
==========

Get up and running with NotifyState in just a few steps!

Installation
------------

Install the latest release from our `GitHub <https://github.com/kAIto47802/NotifyState>`__:

.. code-block:: bash

   pip install git+https://github.com/kAIto47802/NotifyState.git


Set Up Your Platform (e.g., Slack or Discord)
---------------------------------------------

Currently, Slack and Discord are supported.
For setup instructions, please refer to the :doc:`guides` section.


Basic Usage
-----------

For more detailed usage, please refer to the :doc:`api`.


Environment Variables
^^^^^^^^^^^^^^^^^^^^^

You can configure default channels and tokens via environment variables, so that you don't have to pass them directly in your code:

.. code-block:: bash

   # For Slack notifier
   export SLACK_CHANNEL="my-channel"
   export SLACK_BOT_TOKEN="xoxb-1234..."

   # For Discord notifier
   export DISCORD_CHANNEL="1234567890123456789"
   export DISCORD_BOT_TOKEN="ABCD1234..."

Once set, you can omit those parameters:

.. code-block:: python

   import notist

   # Will use SLACK_CHANNEL and SLACK_BOT_TOKEN
   notist.init(send_to="slack")

   with notist.watch():
       ...


.. note::
   The channel and token must be set, either via environment variables or as function arguments.
   If not set, the notification will not be sent, and an error will be logged
   (the original Python script will continue running without interruption).


Configuring Defaults
^^^^^^^^^^^^^^^^^^^^

Once initialized with :func:`~notist._core.init`, you can omit basic settings in subsequent calls.

.. code-block:: python

   import notist

   # Set up Slack notifiers with defaults
   notist.init(send_to="slack", channel="my-channel")

   # Now you can omit these settings in subsequent calls
   with notist.watch():
       # This will use the defaults set in init
       ...


Watch Your Function or Block of Code
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Wrap any function or block of code with the :func:`~notist._core.watch` function to get automatic start/stop/error alerts:

**Use as a decorator to monitor a function**:

.. code-block:: python

   @notist.watch()
   def long_task():
       # This function will be monitored
       # Your long-running code here
       ...

**Use as a context manager to monitor a block of code**:

.. code-block:: python

   with notist.watch():
       # Code inside this block will be monitored
       # Your long-running code here
       ...


Register an Existing Function or Method to be Monitored
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

You can also register an existing function or method to be monitored using the :func:`~notist._core.register` function.
This function corresponds to applying the :func:`~notist._core.watch` decorator to an existing function or method.

If you want to monitor existing functions from libraries:


.. code-block:: python

   import requests

   # Register the `get` function from the `requests` library
   notist.register(requests, "get")

   # Now any time you call `requests.get`, it will be monitored
   response = requests.get("https://example.com/largefile.zip")

If you want to monitor existing methods of classes:

.. code-block:: python

   from transformers import Trainer

   # Register the `train` method of the `Trainer` class
   notist.register(Trainer, "train")

   # Now any time you call `trainer.train()`, it will be monitored
   trainer = Trainer(model=...)
   trainer.train()

If you want to monitor existing methods of specific class instances:

.. code-block:: python

   from transformers import Trainer

   # Create a Trainer instance
   trainer = Trainer(model=...)

   # Register the `train` method of the `trainer` instance
   # This will not affect other instances of Trainer
   notist.register(trainer, "train")

   # Now any time you call `trainer.train()`, it will be monitored
   trainer.train()


Watch Your Iteration (e.g., for Loop)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

You can monitor the progress of an iterable (e.g., for loop) using the :func:`~notist._core.watch_iterable` function:

.. code-block:: python

   # Monitor progress of processing a long-running for loop
   for batch in notist.watch_iterable(train_dataloader, step=10):
      # This loop will be monitored, and you'll receive notifications every 10 iterations.
      ...

.. note::
   The above example does **not** catch exceptions automatically,
   since exceptions raised inside the for loop cannot be caught by the iterator in Python.
   If you also want to be notified when an error occurs, wrap your code in the monitoring context:

   .. code-block:: python

      with notist.watch_iterable(train_dataloader, step=10) as it:
          for batch in it:
              # This loop will be monitored, and you'll receive notifications every 10 iterations.
              # If an error occurs inside this context, you'll be notified immediately.
              ...


Send a One-Off Notification
^^^^^^^^^^^^^^^^^^^^^^^^^^^

You can also send notifications with the :func:`~notist._core.send` function at any point in your code, not just at the start or end of a task:

.. code-block:: python

   # Immediately send "Job finished!" to your Slack channel
   notist.send("Job finished!")

   # You can also send any Python data (it will be stringified)
   notist.send(data)


Custom Notifier Instances
^^^^^^^^^^^^^^^^^^^^^^^^^

Instead of the procedural API, you can also create a notifier instance and call its methods:

.. code-block:: python

   from notist import SlackNotifier

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