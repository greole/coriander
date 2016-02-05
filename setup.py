import sys

from setuptools import setup
from setuptools.command.test import test as TestCommand

package_name = 'coriander'

config = {
    'author'                 : '',
    'author_email'           : '',
    'description'            : '',
    'license'                : '',
    'version'                : "0.0.1",
    'include_package_data'   : True,
    'packages'               : [ "coriander"],
   'name'                    : 'coriander',
}


setup(**config)
