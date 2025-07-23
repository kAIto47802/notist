.. NotifyState documentation master file, created by
   sphinx-quickstart on Sun Jun  8 03:40:33 2025.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

NotifyState: A simple package to send notifications of script execution status
==============================================================================


NotifyState is a lightweight Python package that lets you keep track of your scripts and functions by sending real-time notifications when they start, finish, or encounter errors.
Whether you're running long-running data jobs, background tasks, or simple scripts, NotifyState helps you stay informed without constantly checking your terminal.


Key Features
------------

Real-time Notifications
^^^^^^^^^^^^^^^^^^^^^^^

Get instant updates on the status of your scripts.
You can receive notifications when your script:

- Starts running
- Completes successfully
- Encounters an error
- Or at any point you choose--trigger custom notifications anywhere in your code with any message you like


Easy Integration with Simple API
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

You can use the :func:`~notifystate.watch` helper either as a function decorator or as a context manager around a block of code:

**As a decorator:**

.. code-block:: python

   import notifystate

   @notifystate.watch(send_to="slack", channel="my-channel")
   def long_task():
         # Your long-running code here
         ...


**As a context manager:**

.. code-block:: python

   import notifystate

   with notifystate.watch(send_to="slack", channel="my-channel"):
         # Your long-running code here
         ...

Multiple Notifiers
^^^^^^^^^^^^^^^^^^

Currently supports Slack and Discord. If you need another notifier, feel free to open an issue or a pull request on `GitHub <https://github.com/kAIto47802/NotifyState>`__!


.. toctree::
   :maxdepth: 2
   :caption: Contents:

   quickstart
   api
   guides

Indices and tables
------------------

* :ref:`genindex`
* :ref:`search`