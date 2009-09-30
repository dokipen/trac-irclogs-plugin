from setuptools import setup

PACKAGE = 'irclogs'
VERSION = '0.3'

setup(
    name=PACKAGE,
    version=VERSION,
    description='Display Supybot IRC Logs',
    author='Armin Ronacher, pacopablo, doki_pen',
    author_email='doki_pen@doki-pen.org',
    url='http://trac-hacks.org/wiki/IrcLogsPlugin',
    license='BSD',
    test_suite= 'irclogs.tests.suite',
    packages=['irclogs', 'irclogs.provider'],
    classifiers=[
        'Framework :: Trac',
        'License :: OSI Approved :: BSD License',
    ],
    package_data={
        'irclogs' : ['templates/*.html', 'htdocs/css/*.css', 
                     'htdocs/js/*.js', 'htdocs/images/*.png']
    },
    entry_points = {
        'trac.plugins': [
            'irclogs.api = irclogs.api',
            'irclogs.macros = irclogs.macros',
            'irclogs.nojs = irclogs.nojs',
            'irclogs.search = irclogs.search',
            'irclogs.web_ui = irclogs.web_ui',
            'irclogs.wiki = irclogs.wiki',
            'irclogs.provider.file = irclogs.provider.file',
            'irclogs.provider.db = irclogs.provider.db',
        ],
        'console_scripts': ['update-irc-search = irclogs.console:update_irc_search',],
    },
    install_requires = ['pytz>=2005m'],
    # optional pyndexter
)
