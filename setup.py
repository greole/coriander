import sys

from setuptools import setup
from setuptools.command.test import test as TestCommand

package_name = 'coriander'

config = {
    'author'                 : 'Gregor Olenik',
    'author_email'           : '',
    'description'            : '',
    'license'                : '',
    'version'                : "0.0.1",
    'include_package_data'   : True,
    'packages'               : [ "coriander"],
    'name'                   : 'coriander',
    'entry_points': {'console_scripts': ['coriander = coriander:cli']}
}


setup(**config)
