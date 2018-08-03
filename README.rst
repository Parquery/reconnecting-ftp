reonnecting_ftp
===============

reconnecting_ftp provides a FTP client which wraps ftplib.FTP. It reconnects automatically to the server if it was
disconnected, and remembers the last recorded working directory.

We found reconnection to be particularly important in scripts which run for a long time, and need to repeatedly iterate
over the files on the FTP server.

Since results need to be atomic, we have to convert the result from
``ftplib.FTP.mlsd`` (an iterable of directory entries) to an explicit list of directory entries. While this gives you
atomicity (whatever you iterate over will be done in a single connection), all the directory entries need to be stored
in memory.

Additionally, we provide an implementation of ``mlst`` FTP command which is missing in the original ``ftplib.FTP``
client.



Usage
=====
.. code-block:: python

    import reconnecting_ftp

    with reconnecting_ftp.Client(hostname="some-host.com", port=21, user="some-user", password="some-password") as ftp:
        # change working directory
        ftp.cwd(dirname='/some-dir/some-subdir')

        # you can execute here all the commands as provided in ftplib.FTP. If the connection failed, the command will
        # be retried while it succeeds or the maximum number of retries haven been exhausted..

        # MLST the file
        pth, entry = ftp.mlst(filename='some-file.txt')

        # iterate over a directory entries atomically
        for name, entry_dict in ftp.mlsd(path=parent_path):
            # do something
            pass

Installation
============

* Create a virtual environment:

.. code-block:: bash

    python3 -m venv venv3

* Activate it:

.. code-block:: bash

    source venv3/bin/activate

* Install reconnecting_ftp with pip:

.. code-block:: bash

    pip3 install reconnecting_ftp

Development
===========

* Check out the repository.

* In the repository root, create the virtual environment:

.. code-block:: bash

    python3 -m venv venv3

* Activate the virtual environment:

.. code-block:: bash

    source venv3/bin/activate

* Install the development dependencies:

.. code-block:: bash

    pip3 install -e .[dev]

* We provide a set of pre-commit checks that lint and check code for formatting and runs unit tests. Run them locally
  from an activated virtual environment with development dependencies:

.. code-block:: bash

    ./precommit.py

* The pre-commit script can also automatically format the code:

.. code-block:: bash

    ./precommit.py  --overwrite

Versioning
==========
We follow `Semantic Versioning <http://semver.org/spec/v1.0.0.html>`_. The version X.Y.Z indicates:

* X is the major version (backward-incompatible),
* Y is the minor version (backward-compatible), and
* Z is the patch version (backward-compatible bug fix).