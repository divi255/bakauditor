__version__ = '0.0.15'

import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="bakauditor",
    version=__version__,
    author='Sergei S.',
    author_email="s@makeitwork.cz",
    description="Backup auditor",
    long_description=long_description,
    long_description_content_type='text/markdown',
    url="https://github.com/divi255/bakauditor",
    packages=setuptools.find_packages(),
    license='MIT',
    install_requires=[
        'pyyaml>=6', 'rapidtables', 'neotermcolor', 'python-dateutil>=2.8.2'
    ],
    python_requires='>=3.10',
    entry_points={'console_scripts': ['bakauditor=bakauditor.cli:main']},
    include_package_data=True,
    classifiers=('Programming Language :: Python :: 3',
                 'License :: OSI Approved :: MIT License',
                 'Topic :: System :: Archiving :: Backup'),
)
