class CommandRegistry:
    """
    Register a map from command shortcut to function name
    """

    def __init__(self):
        self.functions = {}

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
            if not shortcuts:
                self.functions[name] = name
            for shortcut in shortcuts:
                self.functions[shortcut] = name
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
