class CommandRegistry:
    """
    Register a map from command shortcut to function name
    """

    def __init__(self):
        self.functions = {}
        self.descriptions = {}
        self.docstrings = {}

    def register(self, shortcuts=None):
        """
        Register a function as a command
        :param shortcuts: list of shortcuts for a function
        :return: decorator
        """
        if shortcuts is None:
            shortcuts = []
        if isinstance(shortcuts, str):
            shortcuts = [shortcuts]

        def wrapper(func):
            name = func.__name__
            doc = func.__doc__
            desc = doc.strip().splitlines()[
                0] if doc else "This docstring is missing!! Abuse @petr_lavrov until he writes it!!"
            if not shortcuts:
                shortcuts.append(f"/{name}")
            for shortcut in shortcuts:
                self.functions[shortcut] = name
                self.descriptions[shortcut] = desc
                self.docstrings[shortcut] = doc
            return func

        return wrapper

    def update(self, commands):
        self.functions.update(commands)

    def list_commands(self):
        """
        List all commands
        :return: List[str]
        """
        return list(self.functions.keys())

    def get_function(self, command):
        return self.functions[command]

    def get_description(self, command):
        return self.descriptions[command]

    def get_docstring(self, command):
        return self.docstrings[command]
