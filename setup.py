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
        'irclogs' : ['templates/*.html', 'htdocs/*.css', 
                     'htdocs/*.js', 'htdocs/*.png']
    },
    entry_points = {
        'trac.plugins': ['irclogs = irclogs'],
        'console_scripts': ['update-irc-search = irclogs.console:update_irc_search',],
    },
    install_requires = ['pyndexter>=0.2', 'pytz>=2005m'],
)
