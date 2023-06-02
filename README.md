<<<<<<< HEAD
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
=======
![PyPI - Python Version](https://img.shields.io/pypi/pyversions/xoa-core) [![PyPI](https://img.shields.io/pypi/v/xoa-core)](https://pypi.python.org/pypi/xoa-core) ![GitHub](https://img.shields.io/github/license/xenanetworks/open-automation-core) [![Documentation Status](https://readthedocs.org/projects/xena-openautomation-core/badge/?version=stable)](https://xena-openautomation-core.readthedocs.io/en/stable/?badge=stable)

# Xena OpenAutomation Core - Test Suite Plugin Library

Xena OpenAutomation Core - Test Suite Plugin Library is the public repository includes multiple automated benchmarking tests and compliance tests, such as RFC 2544, RFC 2889, RFC 3918, and all that will be published in future releases.

To use the test methodologies in XOA Test Suite Plugin Library, you need to install XOA Core. Read the user document of [Xena OpenAutomation Core Documentation](https://docs.xenanetworks.com/projects/xoa-core).

<img src="static/OPENAUTOMATION-2554.png" alt="2544" width="150"/> <img src="static/OPENAUTOMATION-2889.png" alt="2889" width="150"/> <img src="static/OPENAUTOMATION-3918.png" alt="3918" width="150"/>
>>>>>>> 3cc9f0b9d909bf190869951074a9f7671edd76c7
