:html_theme.sidebar_secondary.remove: true

.. rst-class:: center-title

Notist: A Simple Package to Send Notifications of Script Execution Status
==============================================================================

.. rst-class:: center-paragraph

Notist (Notify State) is a lightweight Python package that lets you keep track of your scripts by sending real-time notifications when they start, finish, or encounter errors.
When you're executing long-running jobs or background tasks, Notist helps you stay informed without constantly checking your terminal.

.. raw:: html

   <div align="center" class="badges">
     <a href="https://github.com/kAIto47802/notist">
       <img src="https://img.shields.io/badge/-GitHub-181717.svg?logo=github&style=flat" alt="GitHub">
     </a>
     <a href="https://www.python.org">
       <img src="https://img.shields.io/badge/python-3.9%20%7C%203.10%20%7C%203.11%20%7C%203.12%20%7C%203.13%20%7C%203.14-blue?style=flat" alt="Python">
     </a>
     <a href="https://kaito47802.github.io/notist/index.html">
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

Watch Your Functions, Blocks of Code, or Iterations
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

You can use :func:`~notist._core.watch` to monitor the execution of your functions, blocks of code, or iterations.

**Monitor functions:**

.. code-block:: python

   import notist

   # You can also optionally specify params to include in the notification
   # The values passed to these parameters are also reported
   @notist.watch(params=["arg1", "arg2"])
   def long_task(arg1: int, arg2: str, arg3: bool) -> None:
       # This function will be monitored
       # You can receive notifications when it starts, ends, or encounters an error
       ...
       # Your long-running code here


**Monitor blocks of code:**

.. code-block:: python

   import notist

   with notist.watch():
       # Code inside this block will be monitored
       # You can receive notifications when it starts, ends, or encounters an error
       ...
       # Your long-running code here

**Monitor iterations (e.g., for loops)**:

.. code-block:: python

   # Monitor progress of processing a long-running for loop
   for i in notist.watch(range(100), step=10):
      # This loop will be monitored, and you'll receive notifications every 10 iterations.
      ...


This code example send the following notifications:

- When the function starts running:

  .. code-block:: text

     Start watching <function `__main__.without_error`>
      ▷ Defined at: /home/kaito47802/workspace/notist/sample.py:21
      ▷ Called from: `__main__` @ /home/kaito47802/workspace/notist/sample.py:28


- When the function completes successfully:

  .. code-block:: text

     End watching <function `__main__.without_error`>
      ▷ Defined at: /home/kaito47802/workspace/notist/sample.py:21
      ▷ Called from: `__main__` @ /home/kaito47802/workspace/notist/sample.py:28
      ⦿ Execution time: 0s


- When the function encounters an error:

  .. code-block:: text

     @kAIto47802
     Error while watching <function `__main__.with_error`>
      ▷ Defined at: /home/kaito47802/workspace/notist/sample.py:15
      ▷ Called from: `__main__` @ /home/kaito47802/workspace/notist/sample.py:30
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
     >  File "/home/kaito47802/workspace/notist/sample.py", line 18, in with_error
     >    raise Exception("This is an error")
     > Exception: This is an error

.. note::
   The above example for monitoring iterations does **not** catch exceptions automatically,
   since exceptions raised inside the for loop cannot be caught by the iterator in Python.
   If you also want to be notified when an error occurs, wrap your code in the monitoring context:

   .. code-block:: python

      with notist.watch(range(100), step=10) as it:
          for i in it:
              # This loop will be monitored, and you'll receive notifications every 10 iterations.
              # If an error occurs inside this context, you'll be notified immediately.
              ...
              # Your long-running code here


Register an Existing Function or Method to be Monitored
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

You can also use :func:`~notist._core.register` to register an existing function or method to be monitored.

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

Currently supports Slack and Discord. If you need another notifier, feel free to open an issue or a pull request on `GitHub <https://github.com/kAIto47802/notist>`__!


.. rst-class:: center-title

📦 Installation 📦
------------------
You can install Notist from PyPI or our GitHub:

.. code-block:: bash

   uv add notist
   # If you're using pip:
   # pip install notist


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