from LSP.plugin import LspPlugin


class LspVibescript(LspPlugin):
    pass


def plugin_loaded():
    LspVibescript.register()


def plugin_unloaded():
    LspVibescript.unregister()
