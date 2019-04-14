import command
import module

class TodoModule(module.Module):
    name = 'To-do'

    def on_load(self):
        if 'todo' not in self.bot.config:
            self.bot.config['todo'] = {}
            print('Initialized to-do list data in config')

    @command.desc('Add an item to the todo list')
    @command.alias('t')
    def cmd_todo(self, msg, args):
        if not args:
            return '__Provide an item to add to the todo list.__'
        if args.startswith('list ') or args == "list":
            return self.bot.cmd_todolist(msg, args[5:])
        if args.startswith('del '):
            return self.bot.cmd_tododel(msg, args[4:])

        item = args
        l_name = 'main'

        if l_name not in self.bot.config['todo']:
            self.bot.config['todo'][l_name] = []

        self.bot.config['todo'][l_name].append(item)
        self.bot.save_config()

        idx = len(self.bot.config['todo'][l_name])
        return f'Added item `{item}` as entry {idx}.'

    @command.desc('Show the todo list')
    @command.alias('tl')
    def cmd_todolist(self, msg, l_name):
        if not l_name:
            l_name = 'main'
        if l_name not in self.bot.config['todo']:
            return f'__List \'{l_name}\' doesn\'t exist.'
        if not self.bot.config['todo'][l_name]:
            return '__Todo list is empty.__'

        out = 'Todo list:'

        for idx, item in enumerate(self.bot.config['todo'][l_name]):
            out += f'\n    {idx + 1}. {item}'

        return out

    @command.desc('Delete an item from the todo list')
    @command.alias('td', 'tdd', 'tld', 'tr', 'trm', 'dt', 'done')
    def cmd_tododel(self, msg, idx_str):
        if not idx_str:
            return '__Provide the entry number or entry text to delete.__'
        lst = self.bot.config['todo']['main']

        try:
            idx = int(idx_str)
        except ValueError:
            try:
                idx = lst.index(idx_str) + 1
            except ValueError:
                return '__Invalid entry number or text to delete.__'

        l = len(lst)
        if idx > l:
            return f'__Entry number out of range, there are {l} entries.__'

        idx -= 1
        item = lst[idx]
        del lst[idx]
        self.bot.save_config()

        return f'Item #{idx + 1} `{item}` deleted.'
