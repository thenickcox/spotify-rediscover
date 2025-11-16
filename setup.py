from setuptools import setup, find_packages

authors = "Nick Cox"

setup(
    name='spotify_rediscover_cli',
    version='0.1.0',
    packages=find_packages(),
    description='Spotify Streaming History Analysis CLI',
    install_requires=['pytest'],
)