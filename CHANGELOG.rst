1.1.2
=====
* Added logic to retry on ConnectionError (#21)
* Added logic to retry on ``BrokenPipeError`` (#19)
* Removed support for Python 3.6 and added for 3.11 (#20)
* Added support for Python 3.10 (#16)

1.1.1
=====
* Made encoding keyword backward compatible (#8)
* Added badges and updated supported Python versions (#12)

1.1.0
=====
* Propagated the parameter encoding (#5)

1.0.12
======
* Moved to github.com
* Moved reconnecting_ftp.py to a module directory

1.0.11
======
* Client reconnects on EOFError
