import logging

def debug_enable(*argv):
    debug_modules = (
        '__main__',
        'client_main',
        'dialogs.settings',
        'dialogs.common',
        'dialogs.help',
        'functions.bot_functions',
        'functions.userbot_functions',
        'functions.data_cached'

    )

    if len(argv):
        debug_modules = argv

    for module in debug_modules:
        logging.getLogger(module).setLevel(logging.DEBUG)