.. NotifyState documentation master file, created by
   sphinx-quickstart on Sun Jun  8 03:40:33 2025.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

NotifyState: A Simple Package to Send Notifications of Script Execution Status
==============================================================================


NotifyState is a lightweight Python package that lets you keep track of your scripts and functions by sending real-time notifications when they start, finish, or encounter errors.
Whether you're running long-running data jobs, background tasks, or simple scripts, NotifyState helps you stay informed without constantly checking your terminal.


.. image:: https://img.shields.io/badge/-GitHub-181717.svg?logo=github&style=flat
   :target: https://github.com/kAIto47802/NotifyState
   :alt: GitHub
.. image:: https://img.shields.io/badge/python-3.9%20%7C%203.10%20%7C%203.11%20%7C%203.12-blue
   :target: https://www.python.org
   :alt: Python
.. image:: https://img.shields.io/badge/docs-latest-brightgreen?logo=read-the-docs
   :target: https://kaito47802.github.io/NotifyState/index.html
   :alt: Documentation

✨ Key Features ✨
------------------

⌛ Real-time Notifications
^^^^^^^^^^^^^^^^^^^^^^^^^^

Get instant updates on the status of your scripts.
You can receive notifications when your script:

- Starts running
- Completes successfully
- Encounters an error
- Or at any point you choose--trigger custom notifications anywhere in your code with any message you like


🛠️ Easy Integration with Simple API
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

For more detailed usage, please refer to the :doc:`api` or the :doc:`quickstart` guide.

Watch Your Functions and Blocks of Code
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

You can use the :func:`~notist._core.watch` helper either as a function decorator or as a context manager around a block of code:

**Use as a decorator to monitor a function:**

.. code-block:: python

   import notist

   @notist.watch(send_to="slack", channel="my-channel")
   def long_task():
       # This function will be monitored
       # Your long-running code here
       ...
       # An example where an error occurs during task execution:
       raise Exception("This is an error")


**Or use as a context manager to monitor a block of code:**

.. code-block:: python

   import notist

   with notist.watch(send_to="slack", channel="my-channel"):
       # Code inside this block will be monitored
       # Your long-running code here
       ...

This code example send the following notifications:

- When the function starts running:

   .. code-block:: text

      Start watching [function: long_task]...


- When the function completes successfully:

   .. code-block:: text

      Stop watching [function: long_task].
      Execution time: 2h 32s.


- When the function encounters an error:

   .. code-block:: text

      Error while watching [function: with_error]: This is an error
      Execution time: 2h 32s.
      > Traceback (most recent call last):
      >   File "/home/kaito47802/.pyenv/versions/3.11.0/lib/python3.11/contextlib.py", line 81, in inner
      >     return func(*args, **kwds)
      >            ^^^^^^^^^^^^^^^^^^^
      >   File "/home/kaito47802/workspace/notist/test.py", line 10, in with_error
      >     raise Exception("This is an error")
      > Exception: This is an error

Register an Existing Function or Method to be Monitored
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

You can also register an existing function or method to be monitored using the :func:`~notist._core.register` function.

**Monitor existing functions from libraries:**

.. code-block:: python

   import notist
   import requests

   # Register the `get` function from the `requests` library
   notist.register(requests, "get")

   # Now any time you call `requests.get`, it will be monitored
   response = requests.get("https://example.com/largefile.zip")

**Monitor existing methods of classes:**

.. code-block:: python

   import notist
   from transformers import Trainer

   # Register the `train` method of the `Trainer` class
   notist.register(Trainer, "train")

   # Now any time you call `trainer.train()`, it will be monitored
   trainer = Trainer(model=...)
   trainer.train()

**Monitor existing methods of specific class instances:**

.. code-block:: python

   import notist
   from transformers import Trainer

   # Create a Trainer instance
   trainer = Trainer(model=...)

   # Register the `train` method of the `trainer` instance
   # This will not affect other instances of Trainer
   notist.register(trainer, "train")

   # Now any time you call `trainer.train()`, it will be monitored
   trainer.train()

🔔 Multiple Notifiers
^^^^^^^^^^^^^^^^^^^^^

Currently supports Slack and Discord. If you need another notifier, feel free to open an issue or a pull request on `GitHub <https://github.com/kAIto47802/NotifyState>`__!


📦 Installation 📦
------------------
You can install NotifyState from our GitHub:

.. code-block:: bash

   pip install git+https://github.com/kAIto47802/NotifyState.git



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