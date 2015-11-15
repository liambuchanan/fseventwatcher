#!/usr/bin/env python
from __future__ import print_function
import sys
import threading
try:
    import xmlrpc.client as xmlrpclib
except ImportError:
    import xmlrpclib

from supervisor import childutils
from supervisor.options import make_namespec
from supervisor.states import ProcessStates
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler


class PollableFileSystemEventHandler(FileSystemEventHandler):
    def __init__(self, watch_moved, watch_created, watch_deleted, watch_modified):
        super(PollableFileSystemEventHandler, self).__init__()
        self.watch_moved = watch_moved
        self.watch_created = watch_created
        self.watch_deleted = watch_deleted
        self.watch_modified = watch_modified
        self._activity_occurred = False
        self._lock = threading.Lock()

    def mark_activity_occurred(self):
        with self._lock:
            res = self._activity_occurred
            self._activity_occurred = True
            return res

    def unmark_activity_occurred(self):
        with self._lock:
            res = self._activity_occurred
            self._activity_occurred = False
            return res

    def on_moved(self, event):
        super(PollableFileSystemEventHandler, self).on_moved(event)
        if self.watch_moved:
            self.mark_activity_occurred()

    def on_created(self, event):
        super(PollableFileSystemEventHandler, self).on_created(event)
        if self.watch_created:
            self.mark_activity_occurred()

    def on_deleted(self, event):
        super(PollableFileSystemEventHandler, self).on_deleted(event)
        if self.watch_deleted:
            self.mark_activity_occurred()

    def on_modified(self, event):
        super(PollableFileSystemEventHandler, self).on_modified(event)
        if self.watch_modified:
            self.mark_activity_occurred()


class FSEventWatcher(object):
    def __init__(self, rpc, programs, any_program, paths, recursive, fs_event_handler):
        self.rpc = rpc
        self.programs = programs
        self.any_program = any_program
        self.paths = paths
        self.recursive = recursive
        self.fs_event_handler = fs_event_handler
        self.stdin = sys.stdin
        self.stdout = sys.stdout
        self.stderr = sys.stderr

    def _restart_processes(self):
        try:
            specs = self.rpc.supervisor.getAllProcessInfo()
        except Exception as e:
            print("Unable to get process info: {}. No action taken.".format(e), file=self.stderr)
            self.fs_event_handler.mark_activity_occurred()  # remark to avoid swallowing fs events
        else:
            waiting = set(self.programs)
            for spec in specs:
                name = spec["name"]
                namespec = make_namespec(spec["group"], name)
                if self.any_program or name in waiting or namespec in waiting:
                    if spec["state"] is ProcessStates.RUNNING:
                        print("Restarting process: {}.".format(namespec), file=self.stderr)
                        try:
                            self.rpc.supervisor.stopProcess(namespec)
                        except xmlrpclib.Fault as e:
                            print("Unable to stop process {}: {}.".format(namespec, e), file=self.stderr)
                        try:
                            self.rpc.supervisor.startProcess(namespec)
                        except xmlrpclib.Fault as e:
                            print("Unable to start process {}: {}.".format(namespec, e), file=self.stderr)
                        else:
                            print("Restarted process {}.".format(namespec), file=self.stderr)
                    else:
                        print("Process {} is not in RUNNING state. No action taken.".format(namespec))
                    waiting.discard(name)
                    waiting.discard(namespec)
            if len(waiting) > 0:
                print("Programs specified could not be found: {}.".format(", ".join(waiting)), file=self.stderr)

    def runforever(self):
        observer = Observer()
        for path in self.paths:
            observer.schedule(self.fs_event_handler, path, self.recursive)
        observer.start()
        while True:
            headers, payload = childutils.listener.wait(self.stdin, self.stdout)
            if (headers["eventname"].startswith("TICK") and
                    self.fs_event_handler.unmark_activity_occurred()):
                self._restart_processes()
            childutils.listener.ok(self.stdout)


def main():
    import argparse
    import os
    parser = argparse.ArgumentParser("fseventwatcher",
                                     description="Supervisor TICK event listener which restarts processes "
                                     "if file system changes occur between ticks.")
    parser.add_argument("-p", "--programs", type=str, nargs="*", metavar="PROGRAM",
                        help="Supervisor process name/s to be restarted if in RUNNING state.")
    parser.add_argument("-a", "--any-program", action="store_true",
                        help="Restart any supervisor processes in RUNNING state.")
    parser.add_argument("-f", "--paths", type=str, nargs="+", metavar="PATH", required=True,
                        help="Path to watch for file system events.")
    parser.add_argument("-r", "--recursive", action="store_true",
                        help="Watch path/s recursively.")
    parser.add_argument("--watch-moved", action="store_true",
                        help="Watch file system for 'moved' events.")
    parser.add_argument("--watch-created", action="store_true",
                        help="Watch file system for 'created' events.")
    parser.add_argument("--watch-deleted", action="store_true",
                        help="Watch file system for 'deleted' events.")
    parser.add_argument("--watch-modified", action="store_true",
                        help="Watch file system for 'modified' events.")
    parser.add_argument("--watch-any", action="store_true",
                        help="Watch file system for any event")
    # parser.add_argument("--files-only", action="store_true")
    # parser.add_argument("--dirs-only", action="store_true")
    # parser.add_argument("--regex")
    # parser.add_argument("--dither", type=int)
    args = parser.parse_args()
    if not(args.programs or args.any_program):
        parser.error("Must specify either -p, --programs or -a, --any-program.")
    for path in args.paths:
        if not(os.path.exists(path)):
            parser.error("Path {} does not exits.".format(path))
    if not(args.watch_moved or args.watch_created or args.watch_deleted or args.watch_modified or args.watch_any):
        parser.error("Must specify which event/s to watch.")
    if args.files_only and args.dirs_only:
        parser.error("Must specify one/none of --files-only and --dirs-only.")

    try:
        rpc = childutils.getRPCInterface(os.environ)
    except KeyError as e:
        if e.args[0] == "SUPERVISOR_SERVER_URL":
            print("fseventwatcher must be run as a supervisor event listener.", file=sys.stderr)
            sys.exit(1)
        else:
            raise

    if args.watch_any:
        fs_event_handler = PollableFileSystemEventHandler(True, True, True, True)
    else:
        fs_event_handler = PollableFileSystemEventHandler(
            args.watch_moved, args.watch_created, args.watch_deleted, args.watch_modified)

    fseventwatcher = FSEventWatcher(
        rpc, args.programs or [], args.any_program, args.paths, args.recursive, fs_event_handler)
    fseventwatcher.runforever()


if __name__ == "__main__":
    main()
