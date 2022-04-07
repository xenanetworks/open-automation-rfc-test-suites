![PyPI - Python Version](https://img.shields.io/pypi/pyversions/xoa-test-suites) [![PyPI](https://img.shields.io/pypi/v/xoa-test-suites)](https://pypi.python.org/pypi/xoa-test-suites)
# Xena OpenAutomation Test Suites

## Introduction


## Key Features


## Documentation
The user documentation is hosted:



## Quick Start

* Get Python pip if not already installed (Download https://bootstrap.pypa.io/get-pip.py):
    `python get-pip.py`

* Install the latest xoa-driver:
    `pip install xoa-test-suites -U`

* Write Python code to start 2544 tests:
    `python`
    ```python
    import asyncio


    async def my_awesome_script():
        

    def main():
    try:
        loop = asyncio.get_event_loop()
        loop.create_task(my_awesome_script())
        loop.run_forever()
    except KeyboardInterrupt:
        pass

    if __name__ == "__main__":
        main()
    ```


## Installation

### Install Using `pip`
Make sure Python `pip` is installed on you system. If you are using virtualenv, then pip is already installed into environments created by virtualenv, and using sudo is not needed. If you do not have pip installed, download this file: https://bootstrap.pypa.io/get-pip.py and run `python get-pip.py`.

To install the latest, use pip to install from pypi:
``` shell
~/> pip install xoa-test-suites
```

To upgrade to the latest, use pip to upgrade from pypi:
``` shell
~/> pip install xoa-test-suites --upgrade
```

### Install From Source Code
Make sure these packages are installed ``wheel``, ``setuptools`` on your system.

Install ``setuptools`` using pip:
``` shell
~/> pip install wheel setuptools
```

To install source of python packages:
``` shell
/xoa_test_suites> python setup.py install
```

To build ``.whl`` file for distribution:
``` shell
/xoa_test_suites> python setup.py bdist_wheel
```


***

Uɴɪғɪᴇᴅ. Oᴘᴇɴ. Iɴᴛᴇɢʀᴀᴛɪᴏɴ.