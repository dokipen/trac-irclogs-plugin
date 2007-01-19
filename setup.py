from setuptools import setup

PACKAGE = 'irclogs'
VERSION = '0.2'

setup(
    name=PACKAGE,
    version=VERSION,
    description='Display Supybot IRC Logs',
    author='Armin Ronacher',
    author_email='armin.ronacher@active-4.com',
    url='http://trac.pocoo.org/',
    license='BSD',
    packages=['irclogs'],
    classifiers=[
        'Framework :: Trac',
        'License :: OSI Approved :: BSD License',
    ],
    package_data={
        'irclogs' : ['templates/*.html', 'htdocs/*.css']
    },
    entry_points = {
        'trac.plugins': ['irclogs = irclogs']
    }
)
