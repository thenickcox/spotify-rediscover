from setuptools import setup, find_packages

setup(
    name='spotify-rediscover',
    version='0.1.0',
    packages=find_packages(where='src'),
    package_dir={'': 'src'},
    install_requires=[
        # Add any dependencies here
    ],
    entry_points={
        'console_scripts': [
            'spotify-rediscover=spotify_rediscover_cli:main',
        ],
    },
    author='Your Name',
    author_email='your.email@example.com',
    description='A tool for analyzing Spotify listening history',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    url='https://github.com/yourusername/spotify-rediscover',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: End Users/Desktop',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
    ],
)