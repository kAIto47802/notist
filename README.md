
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
  NotifyState is a lightweight Python package that lets you keep track of your scripts and functions by sending real-time notifications when they start, finish, or encounter errors.
  Whether you're running long-running data jobs, background tasks, or simple scripts, NotifyState helps you stay informed without constantly checking your terminal.
</p>

<div align="center">
  <a target="_blank" href="https://www.python.org">
    <img src="https://img.shields.io/badge/python-3.9%20%7C%203.10%20%7C%203.11%20%7C%203.12-blue" alt="Python"/>
  </a>
  <a href="https://kaito47802.github.io/notifystate/index.html">
    <img src="https://img.shields.io/badge/docs-latest-brightgreen?logo=read-the-docs" alt="Documentation"/>
  </a>
</div>

<br><br>

<h2 align="center">
  ✨ Key Features ✨
</h2>

For the detailed usage and quick start guide, please refer to the [documentation](https://kaito47802.github.io/notifystate/index.html).


<h3>
  <div>⌛ Real-time Notifications</div>
  <a href="https://github.com/kAIto47802/NotifyState/blob/main/README.md">
    <img width="70%" height="6px" src="docs/_images/line3.svg">
</a>
</h3>

Get instant updates on the status of your scripts.
You can receive notifications when your script:

- Starts running
- Completes successfully
- Encounters an error
- Or at any point you choose–trigger custom notifications anywhere in your code with any message you like


<h3>
  <div>🛠️ Easy Integration with Simple API</div>
  <a href="https://github.com/kAIto47802/NotifyState/blob/main/README.md">
    <img width="70%" height="6px" src="docs/_images/line3.svg">
  </a>
</h3>

You can use the `notifystate.watch` helper either as a function decorator or as a context manager around a block of code:

**As a decorator:**

```python
import notifystate

@notifystate.watch(send_to="slack", channel="my-channel")
def long_task():
    # Your long-running code here
    ...
    # An example where an error occurs during task execution:
    raise Exception("This is an error")
```

**As a context manager:**

```python
import notifystate

with notifystate.watch(send_to="slack", channel="my-channel"):
    # Your long-running code here
    ...
```

This code example send the following notifications:

- When the function starts running:

   ```text
   Start watching [function: long_task]...
   ```

- When the function completes successfully:

   ```text
   Stop watching [function: long_task].
   Execution time: 2h 32s.
   ```

- When the function encounters an error:

   ```text
   Error while watching [function: with_error]: This is an error
   Execution time: 2h 32s.
   > Traceback (most recent call last):
   >   File "/home/kaito47802/.pyenv/versions/3.11.0/lib/python3.11/contextlib.py", line 81, in inner
   >     return func(*args, **kwds)
   >            ^^^^^^^^^^^^^^^^^^^
   >   File "/home/kaito47802/workspace/notifystate/test.py", line 10, in with_error
   >     raise Exception("This is an error")
   > Exception: This is an error
   ```

You can also add mentions when necessary.




<h3>
  <div>🔔 Multiple Notifiers</div>
  <a href="https://github.com/kAIto47802/NotifyState/blob/main/README.md">
    <img width="70%" height="6px" src="docs/_images/line3.svg">
  </a>
</h3>


Currently supports Slack and Discord. If you need another notifier, feel free to open an issue or a pull request!


<h2 align="center">
  📦 Installation 📦
</h2>

You can install NotifyState from our GitHub:

```bash
pip install git+https://github.com/kAIto47802/NotifyState.git
```