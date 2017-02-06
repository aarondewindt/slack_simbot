from setuptools import setup, find_packages
from distutils.util import convert_path

main_ns = {}
ver_path = convert_path('slack_simbot/__init__.py')
with open(ver_path) as ver_file:
    exec(ver_file.read(), main_ns)

setup(
    name='slack_simbot',
    version=main_ns['__version__'],
    description='Slack bot fo sending out simulations notifications.',
    author='Aaron de Windt',
    author_email='aaron.dewindt@gmail.com',

    install_requires=['slackclient'],
    packages=find_packages('.', exclude=["test"]),

    classifiers=[
        'Programming Language :: Python :: 3 :: Only',
        'Development Status :: 2 - Pre-Alpha'],
)
