from __future__ import print_function
from collections import namedtuple
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


WatchFileSystemEvents = namedtuple(
    "WatchFileSystemEvents",
    ("moved", "created", "deleted", "modified")
)


class PollableFileSystemEventHandler(FileSystemEventHandler):
    def __init__(self, watch_events):
        super(PollableFileSystemEventHandler, self).__init__()
        self.watch_events = watch_events
        self._activity_occurred = False
        self._lock = threading.Lock()

    def mark_activity_occurred(self):
        with self._lock:
            self._activity_occurred = True

    def reset_activity_occurred(self):
        with self._lock:
            res = self._activity_occurred
            self._activity_occurred = False
            return res

    def on_moved(self, event):
        super(PollableFileSystemEventHandler, self).on_moved(event)
        if self.watch_events.moved:
            self.mark_activity_occurred()

    def on_created(self, event):
        super(PollableFileSystemEventHandler, self).on_created(event)
        if self.watch_events.created:
            self.mark_activity_occurred()

    def on_deleted(self, event):
        super(PollableFileSystemEventHandler, self).on_deleted(event)
        if self.watch_events.deleted:
            self.mark_activity_occurred()

    def on_modified(self, event):
        super(PollableFileSystemEventHandler, self).on_modified(event)
        if self.watch_events.modified:
            self.mark_activity_occurred()


class FSEventWatcher(object):
    def __init__(self, rpc, programs, any, watch_events, path, recursive):
        """
        Possible additions
            - specifying whether files/dirs/both should be watched
            - eager flag
            - email/sendmail
            - coredir/gcore
        """
        self.rpc = rpc
        self.programs = programs
        self.any = any
        self.watch_events = watch_events
        self.path = path
        self.recursive = recursive
        self.stdin = sys.stdin
        self.stdout = sys.stdout
        self.stderr = sys.stderr

    def _restart_processes(self):
        try:
            specs = self.rpc.supervisor.getAllProcessInfo()
        except Exception as e:
            print("Unable to get process info: {}. No action taken.".format(e), file=self.stderr)
        else:
            waiting = set(self.programs)
            for spec in specs:
                name = spec["name"]
                namespec = make_namespec(spec["group"], name)
                if self.any or name in waiting or namespec in waiting:
                    if spec["state"] is ProcessStates.RUNNING:
                        print("Restarting process: {}.".format(namespec), file=self.stderr)
                        try:
                            self.rpc.supervisor.stopProcess(namespec)
                        except xmlrpclib.Fault as e:
                            print("Unable to stop process {}: {}.".format(namespec, e), file=self.stderr)
                        try:
                            self.rpc.supervisor.startProcess(namespec)
                        except xmlrpclib.Fault as e:
                            print("Unable to stop process {}: {}.".format(namespec, e), file=self.stderr)
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
        fs_event_handler = PollableFileSystemEventHandler(self.watch_events)
        observer.schedule(fs_event_handler, self.path, self.recursive)
        observer.start()
        while True:
            headers, payload = childutils.listener.wait(self.stdin, self.stdout)
            if (
                headers["eventname"].startswith("TICK") and
                fs_event_handler.reset_activity_occurred()
            ):
                self._restart_processes()
            childutils.listener.ok(self.stdout)


def main():
    import argparse
    import os
    parser = argparse.ArgumentParser()
    parser.add_argument("-p", "--programs", type=str, nargs="*", metavar="PROGRAM")
    parser.add_argument("-a", "--any", action="store_true")
    parser.add_argument("-r", "--recursive", action="store_true")
    parser.add_argument("path")
    args = parser.parse_args()

    try:
        rpc = childutils.getRPCInterface(os.environ)
    except KeyError as e:
        if e.args[0] == "SUPERVISOR_SERVER_URL":
            print("fseventwatcher must be run as a supervisor event listener.", file=sys.stderr)
            sys.exit(1)
        else:
            raise

    fseventwatcher = FSEventWatcher(
        rpc, args.programs, args.any, WatchFileSystemEvents(True, True, True, True), args.path, args.recursive
    )
    fseventwatcher.runforever()


if __name__ == "__main__":
    main()
