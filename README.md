
<h1 align="center">
  <a href="https://github.com/kAIto47802/NotifyState/blob/main/README.md">
    <img width="97%" height="14px" src="docs/_images/titleLine3t.svg">
  </a>
  NotifyState: A Simple Package to Send Notifications of Script Execution Status
  <a href="https://github.com/kAIto47802/NotifyState/blob/main/README.md">
    <img width="97%" height="14px" src="docs/_images/titleLine3t.svg">
  </a>
</h1>

<p align="center">
  NotifyState is a lightweight Python package that lets you keep track of your scripts by sending real-time notifications when they start, finish, or encounter errors.
  When you're executing long-running jobs or background tasks, NotifyState helps you stay informed without constantly checking your terminal.
</p>

<div align="center">
  <a target="_blank" href="https://www.python.org">
    <img src="https://img.shields.io/badge/python-3.9%20%7C%203.10%20%7C%203.11%20%7C%203.12-blue" alt="Python"/>
  </a>
  <a href="https://kaito47802.github.io/NotifyState/index.html">
    <img src="https://img.shields.io/badge/docs-latest-brightgreen?logo=read-the-docs" alt="Documentation"/>
  </a>
</div>

<br><br>

<h2 align="center">
  ✨ Key Features ✨
</h2>

For the detailed usage and quick start guide, please refer to the [documentation](https://kaito47802.github.io/NotifyState/index.html).


<h3>
  <div>⌛ Real-time Notifications</div>
  <a href="https://github.com/kAIto47802/NotifyState/blob/main/README.md">
    <img width="70%" height="6px" src="docs/_images/line3.svg">
</a>
</h3>

Get instant updates on the status of your scripts.
You can receive notifications when your script:

- starts running;
- completes successfully; or
- encounters an error.


<h3>
  <div>🛠️ Easy Integration with Simple API</div>
  <a href="https://github.com/kAIto47802/NotifyState/blob/main/README.md">
    <img width="70%" height="6px" src="docs/_images/line3.svg">
  </a>
</h3>

#### Watch Your Functions and Blocks of Code

You can use the `notist.watch` helper either as a function decorator or as a context manager around a block of code:

**Use as a decorator to monitor a function:**

```python
import notist

# You can also specify params to include in the notification
# The values passed to these parameters are also reported
@notist.watch(params=["arg1", "arg2"])
def long_task(arg1: int, arg2: str, arg3: bool) -> None:
    # This function will be monitored
    # You can receive notifications when it starts, ends, or encounters an error
    ...
    # Your long-running code here
```

**Use as a context manager to monitor a block of code:**

```python
import notist

with notist.watch():
    # Code inside this block will be monitored
    # You can receive notifications when it starts, ends, or encounters an error
    ...
    # Your long-running code here
```

This code example send the following notifications:

- When the function starts running:

   ```text
   Start watching <function `__main__.without_error`>
    ▷ Defined at: /home/kaito47802/workspace/NotifyState/sample.py:21
    ▷ Called from: `__main__` @ /home/kaito47802/workspace/NotifyState/sample.py:28
   ```

- When the function completes successfully:

   ```text
   End watching <function `__main__.without_error`>
    ▷ Defined at: /home/kaito47802/workspace/NotifyState/sample.py:21
    ▷ Called from: `__main__` @ /home/kaito47802/workspace/NotifyState/sample.py:28
    ⦿ Execution time: 0s
   ```

- When the function encounters an error:

   ```text
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
   ```

#### Register an Existing Function or Method to be Monitored

You can also register an existing function or method to be monitored using the `notist.register` function.

**Monitor existing functions from libraries:**

```python
import notist
import requests

# Register the `get` function from the `requests` library
notist.register(requests, "get")

# Now any time you call `requests.get`, it will be monitored
response = requests.get("https://example.com/largefile.zip")
```

**Monitor existing methods of classes:**

```python
import notist
from transformers import Trainer

# Register the `train` method of the `Trainer` class
notist.register(Trainer, "train")

# Now any time you call `trainer.train()`, it will be monitored
trainer = Trainer(model=...)
trainer.train()
```

**Monitor existing methods of specific class instances:**

```python
import notist
from transformers import Trainer

# Create a Trainer instance
trainer = Trainer(model=...)

# Register the `train` method of the `trainer` instance
# This will not affect other instances of Trainer
notist.register(trainer, "train")

# Now any time you call `trainer.train()`, it will be monitored
trainer.train()
```

We also provide other features such as `send` and `watch_iterable`. See the document for details:
<a href="https://kaito47802.github.io/NotifyState/index.html">
  <img src="https://img.shields.io/badge/docs-latest-brightgreen?logo=read-the-docs" alt="Documentation" align="top"/>
</a>


<h3>
  <div>🔔 Multiple Notifiers</div>
  <a href="https://github.com/kAIto47802/NotifyState/blob/main/README.md">
    <img width="70%" height="6px" src="docs/_images/line3.svg">
  </a>
</h3>


Currently supports Slack and Discord. If you need another notifier, feel free to open an issue or a pull request!

<br>

<h2 align="center">
  📦 Installation 📦
</h2>

You can install NotifyState from our GitHub:

```bash
pip install git+https://github.com/kAIto47802/NotifyState.git
```