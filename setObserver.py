#!/usr/bin/env python3

from watchdog.observers import Observer
from watchdog.tricks import ShellCommandTrick
from watchdog.events import PatternMatchingEventHandler
from watchdog.events import LoggingEventHandler
from watchdog.events import FileSystemEventHandler
from pathtools.patterns import match_any_paths
from watchdog.utils import has_attribute
from watchdog.utils import unicode_paths
import yaml
import os
import subprocess


class DirWatch:
    """
    Definition of overall setting for the directory under dirwatch
    """
    def __init__(self, watch_dir, config_file, dirwatch_dir):
        """
        Hold dirwatch parameters
        """
        self.watch_dir = watch_dir
        self.dirwatch_dir = dirwatch_dir
        self.options = self.Options()
        self.tmpwatch = self.Tmpwatch()
        self.scenarios = []aaaa
        self.observer = Observer()
        self.config_file = config_file

    class Options:
        """Sublevel overall options: options"""
        def __init__(self):
            self.recursive = True  # recurse into any subdirectories
            self.files = True      # trigger action only for files
            self.follow = True     # follow symlinks

    class Tmpwatch:
        """
        Sublevel overall options: tmpwatch
        This is not implemented with watchdog, created for placeholder
        """
        def __init__(self):
            self.metric = 'atime'
            self.all = False
            self.nodirs = False
            self.force = True
            self.age = 5           # days

    class Rules:
        def __init__(self):
            self.actions = None  # updated, modified, created
            self.type = 'stdin'
            self.command = None
            self.pattern = None
            self.timing = 'sync'
            self.output = True
            self.number = 0        # scenario id

    def read_config(self):
        with open(self.config_file, 'r') as stream:
            conf = yaml.safe_load(stream)
        self.options.recursive = conf['options']['recursive']
        self.options.files = conf['options']['files']
        self.options.follow = conf['options']['follow']
        for act in list(conf['actions'].keys()):
            temp = self.Rules
            temp.actions = act
            nm = 0
            for m in list(conf['actions'][act]):
                temp.number = nm
                nm += 1
                try:
                    temp.command = m['command']
                except KeyError:
                    print('Command setting not found.')
                    raise
                try:
                    temp.pattern = m['pattern']
                except KeyError:
                    print('Pattern setting not found')
                    raise
                try:
                    temp.type = m['type']
                except KeyError:
                    print('Type setting not found, use stdin.')
                    temp.type = 'stdin'
                try:
                    temp.timing = m['timing']
                except KeyError:
                    print('Timing setting not found, use sync.')
                    temp.timing = 'sync'
                try:
                    temp.output = m['output']
                except KeyError:
                    print('Output setting not found, use true')
                    temp.output = True
            self.scenarios.append(temp)

    def stage_scenarios(self):

        if self.options.follow:
            watch_dir = os.path.realpath(self.watch_dir)
        else:
            watch_dir = self.watch_dir

        for rules in self.scenarios:

            event_handler = PatternMatchingEventHandler(patterns=rules.pattern,
                                                        ignore_directories=self.options.files)
            # log_handler = self.PatternMatchingLoggingEventHandler(patterns=rules.pattern,
            #                                                       ignore_directories=self.options.files,
            #                                                       rule_id=rules.number,
            #                                                       action=rules.actions,
            #                                                       log_dir=self.dirwatch_dir)
            cmd_handler = self.EogShellCommandTrick(shell_command=rules.command,
                                                    )
            if rules.action == 'update':  # create or modified
                event_handler.on_modified = cmd_handler.on_any_event
                event_handler.on_created = cmd_handler.on_any_event
                # log_handler.on_modified = log_handler.append_log
                # log_handler.on_created = log_handler.append_log
            elif rules.action == 'created':
                event_handler.on_created = cmd_handler.on_any_event
                # log_handler.on_created = log_handler.append_log
            elif rules.action == 'modified':
                event_handler.on_modified = cmd_handler.on_any_event
                # log_handler.on_modified = log_handler.append_log
            elif rules.action == 'deleted':
                event_handler.on_deleted = cmd_handler.on_any_event
                # log_handler.on_deleted = log_handler.append_log
            elif rules.action == 'existing':   # this is not a exact mapping
                event_handler.on_any_event = cmd_handler.on_any_event
                # log_handler.on_any_event = log_handler.append_log

            self.observer.schedule(event_handler,
                                   watch_dir,
                                   recursive=self.options.recursive)

    # class EogLogger()

    class EogShellCommandTrick(ShellCommandTrick):

        def __init__(self,shell_command=None, patterns=None, ignore_patterns=None,
                     ignore_directories=False, wait_for_process=False,
                      drop_during_process=False):
            super().__init__()

        def on_any_event(self, event):
            from string import Template

            if self.drop_during_process and self.process and self.process.poll() is None:
                return

            if event.is_directory:
                object_type = 'directory'
            else:
                object_type = 'file'

            context = {
                'watch_src_path': event.src_path,
                'watch_dest_path': '',
                'watch_event_type': event.event_type,
                'watch_object': object_type,
            }

            if self.shell_command is None:
                if has_attribute(event, 'dest_path'):
                    context.update({'dest_path': event.dest_path})
                    command = 'echo "${watch_event_type} ${watch_object} from ${watch_src_path} to ${watch_dest_path}"'
                else:
                    command = 'echo "${watch_event_type} ${watch_object} ${watch_src_path}"'
            else:
                if has_attribute(event, 'dest_path'):
                    context.update({'watch_dest_path': event.dest_path})
                command = ' '.join([self.shell_command, '${watch_src_path}'])

            command = Template(command).safe_substitute(**context)
            self.process = subprocess.Popen(command, shell=True)
            if self.wait_for_process:
                self.process.wait()

    class PatternMatchingLoggingEventHandler(PatternMatchingEventHandler):
        """
        Matches given patterns with file paths associated with occurring event, and log it
        to given file.
        """

        def __init__(self, patterns=None, ignore_patterns=None,
                     ignore_directories=False, case_sensitive=False,
                     rule_id=0, action=None, log_dir=None):
            super().__init__(patterns=patterns, ignore_patterns=ignore_patterns,
                             ignore_directories=ignore_directories, case_sensitive=case_sensitive)
            self._rule_id = rule_id
            self._log_dir = log_dir
            self._action = action

        def append_log(self, event):
            log_file = os.path.join(self._log_dir,
                                    '.'.join([self._action,str(self._rule_id), 'log']))
            with open(log_file, 'a') as logger:
                logger.write('i__ '+event.src_path)

        def dispatch(self, event):
            if self.ignore_directories and event.is_directory:
                return

            paths = []
            if has_attribute(event, 'dest_path'):
                paths.append(unicode_paths.decode(event.dest_path))
            if event.src_path:
                paths.append(unicode_paths.decode(event.src_path))

            if match_any_paths(paths,
                               included_patterns=self.patterns,
                               excluded_patterns=self.ignore_patterns,
                               case_sensitive=self.case_sensitive):
                self.on_any_event(event)
                _method_map = {
                    EVENT_TYPE_MODIFIED: self.on_modified,
                    EVENT_TYPE_MOVED: self.on_moved,
                    EVENT_TYPE_CREATED: self.on_created,
                    EVENT_TYPE_DELETED: self.on_deleted,
                }
                event_type = event.event_type
                _method_map[event_type](event)



    def start(self):

        self.observer.start()

class Logger():
