from setuptools import setup
setup(
    name="FSxUtil",
    version='0.0.1',
    packages=['fsxutil'],
    description='FSx utility',
    author='Duke P. Takle',
    author_email='duke.takle@gmail.com',
    install_requires=[
        "boto3>=1.9",
        "requests>=2.18",
        "Click>=7.0"
    ],
    entry_points="""
        [console_scripts]
        fsxutil=fsxutil.command:cli
    """
)
