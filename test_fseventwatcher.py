import unittest
from fseventwatcher import WatchedFileSystemEvents, PollableFileSystemEventHandler, FSEventWatcher


class TestPollableFileSystemEventHandler(unittest.TestCase):
    def test_mark_unmark_activity_occurred(self):
        pfseh = PollableFileSystemEventHandler(None)
        prev = pfseh.mark_activity_occurred()
        self.assertEqual(prev, False)
        prev = pfseh.mark_activity_occurred()
        self.assertEqual(prev, True)

    def test_unmark_activity_occurred(self):
        pfseh = PollableFileSystemEventHandler(None)
        prev = pfseh.unmark_activity_occurred()
        self.assertEqual(prev, False)
        prev = pfseh.mark_activity_occurred()
        prev = pfseh.unmark_activity_occurred()
        self.assertEqual(prev, True)
