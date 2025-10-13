:html_theme.sidebar_secondary.remove: true

.. rst-class:: center-title

NotifyState: A Simple Package to Send Notifications of Script Execution Status
==============================================================================

.. rst-class:: center-paragraph

NotifyState is a lightweight Python package that lets you keep track of your scripts by sending real-time notifications when they start, finish, or encounter errors.
When you're executing long-running jobs or background tasks, NotifyState helps you stay informed without constantly checking your terminal.

.. raw:: html

   <div align="center" class="badges">
     <a href="https://github.com/kAIto47802/NotifyState">
       <img src="https://img.shields.io/badge/-GitHub-181717.svg?logo=github&style=flat" alt="GitHub">
     </a>
     <a href="https://www.python.org">
       <img src="https://img.shields.io/badge/python-3.9%20%7C%203.10%20%7C%203.11%20%7C%203.12-blue?style=flat" alt="Python">
     </a>
     <a href="https://kaito47802.github.io/NotifyState/index.html">
       <img src="https://img.shields.io/badge/docs-latest-brightgreen?logo=read-the-docs&style=flat" alt="Documentation">
     </a>
   </div>

.. rst-class:: center-title

✨ Key Features ✨
------------------

⌛ Real-time Notifications
^^^^^^^^^^^^^^^^^^^^^^^^^^

Get instant updates on the status of your scripts.
You can receive notifications when your script:

- starts running;
- completes successfully; or
- encounters an error.


🛠️ Easy Integration with Simple API
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

For more detailed usage, please refer to the :doc:`api` or the :doc:`quickstart` guide.

Watch Your Functions and Blocks of Code
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

You can use the :func:`~notist._core.watch` helper either as a function decorator or as a context manager around a block of code:

**Use as a decorator to monitor a function:**

.. code-block:: python

   import notist

   # You can also specify params to include in the notification
   # The values passed to these parameters are also reported
   @notist.watch(params=["arg1", "arg2"])
   def long_task(arg1: int, arg2: str, arg3: bool) -> None:
       # This function will be monitored
       # You can receive notifications when it starts, ends, or encounters an error
       ...
       # Your long-running code here


**Use as a context manager to monitor a block of code:**

.. code-block:: python

   import notist

   with notist.watch():
       # Code inside this block will be monitored
       # You can receive notifications when it starts, ends, or encounters an error
       ...
       # Your long-running code here

This code example send the following notifications:

- When the function starts running:

  .. code-block:: text

     Start watching <function `__main__.without_error`>
      ▷ Defined at: /home/kaito47802/workspace/NotifyState/sample.py:21
      ▷ Called from: `__main__` @ /home/kaito47802/workspace/NotifyState/sample.py:28


- When the function completes successfully:

  .. code-block:: text

     End watching <function `__main__.without_error`>
      ▷ Defined at: /home/kaito47802/workspace/NotifyState/sample.py:21
      ▷ Called from: `__main__` @ /home/kaito47802/workspace/NotifyState/sample.py:28
      ⦿ Execution time: 0s


- When the function encounters an error:

  .. code-block:: text

     @kAIto47802
     Error while watching <function `__main__.with_error`>
      ▷ Defined at: /home/kaito47802/workspace/NotifyState/sample.py:15
      ▷ Called from: `__main__` @ /home/kaito47802/workspace/NotifyState/sample.py:30
       29 │     print("Example function that raises an error")
       30 │     with_error()
     ╭───────┄┄ ────────────
     │ 31 │     print("You will see a Slack notification for the error above")
     │ 32 │     print(
     │ 33 │         "You can use the watch() helper as a function decorator or as a context manager"
     ╰─❯ Exception: This is an error
      ⦿ Execution time: 0s

     > Traceback (most recent call last):
     >  File "/home/kaito47802/.pyenv/versions/3.12.0/lib/python3.12/contextlib.py", line 81, in inner
     >    return func(*args, **kwds)
     >           ^^^^^^^^^^^^^^^^^^^
     >  File "/home/kaito47802/workspace/NotifyState/sample.py", line 18, in with_error
     >    raise Exception("This is an error")
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

We also provide other features such as :func:`~notist._core.send` and :func:`~notist._core.watch_iterable`. See :doc:`api` for details.


🔔 Multiple Notifiers
^^^^^^^^^^^^^^^^^^^^^

Currently supports Slack and Discord. If you need another notifier, feel free to open an issue or a pull request on `GitHub <https://github.com/kAIto47802/NotifyState>`__!


.. rst-class:: center-title

📦 Installation 📦
------------------
You can install NotifyState from our GitHub:

.. code-block:: bash

   pip install git+https://github.com/kAIto47802/NotifyState.git


Contents
--------

.. toctree::
   :maxdepth: 2

   quickstart
   api
   guides

Indices and tables
------------------

* :ref:`genindex`
* :ref:`search`