__version__ = '0.0.4'

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
    install_requires=['pyyaml', 'rapidtables', 'neotermcolor'],
    scripts=['bin/bakauditor'],
    include_package_data=True,
    classifiers=('Programming Language :: Python :: 3',
                 'License :: OSI Approved :: MIT License',
                 'Topic :: System :: Archiving :: Backup'),
)
