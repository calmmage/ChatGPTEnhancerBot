from functools import lru_cache


class CommandRegistry:
    """
    Register a map from command shortcut to function name
    """

    def __init__(self):
        self._functions = {}
        self._descriptions = {}
        self._docstrings = {}
        self._groups = {}
        self._active = {}
        # self._is_markdown_safe = {}

    # def register(self, shortcuts=None, group=None, is_markdown_safe=False):
    def register(self, shortcuts=None, group=None, active=True):
        """
        Register a function as a command
        :param shortcuts: list of shortcuts for a function
        :param group: group of the command (for sorting - topic, model, parameters, etc.)
        :return: decorator
        """
        if shortcuts is None:
            shortcuts = []
        if isinstance(shortcuts, str):
            shortcuts = [shortcuts]

        def wrapper(func):
            name = func.__name__
            doc = func.__doc__
            if not shortcuts:
                shortcuts.append(f"/{name}")
            # self.add_command(name, shortcuts, doc, group or func.__class__, is_markdown_safe=is_markdown_safe)
            self.add_command(name, shortcuts, doc, group or func.__class__, active=active)

            func.__shortcuts__ = shortcuts
            return func

        return wrapper

    # def add_command(self, command, shortcuts, docstring, group, is_markdown_safe=False):
    def add_command(self, command, shortcuts, docstring: str, group, active: bool):
        if docstring is not None and docstring.strip():
            desc = docstring.strip().splitlines()[0]
        else:
            desc = "This docstring is missing!! Abuse @petr_lavrov until he writes it!!"

        for shortcut in shortcuts:
            self._functions[shortcut] = command
            self._descriptions[shortcut] = desc
            self._docstrings[shortcut] = docstring
            self._groups[shortcut] = group
            self._active[shortcut] = active
            # self._is_markdown_safe[shortcut] = is_markdown_safe

        # todo: add command as a separate object as well - avoid duplication in help command. Dataclass?

    def update(self, commands):
        self._functions.update(commands)

    @lru_cache(maxsize=1)
    def list_commands(self):
        """
        List all commands
        :return: List[str]
        """
        return sorted(self._functions.keys(), key=self.get_group)

    def get_function(self, command):
        return self._functions[command]

    def get_description(self, command):
        return self._descriptions[command]

    def get_docstring(self, command):
        return self._docstrings[command]

    def get_group(self, command):
        return self._groups[command]

    def is_active(self, command):
        return self._active[command]
    # def is_markdown_safe(self, command):
    #     return self._is_markdown_safe[command]
