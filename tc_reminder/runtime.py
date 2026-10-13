"""Frame freshness and selection evidence, independent of GUI and Windows APIs."""
class SelectionEvidence:
    """Learn visible TC selections without knowing or observing any hotkey."""
    def __init__(self):
        self.count=None
        self.frames=0
        self.last_capture=None

    def observe(self, count, captured_at, safe):
        if not safe or count is None or count < 1:
            self.__init__()
            return False
        if self.last_capture is not None and captured_at<=self.last_capture:
            return False
        if (count!=self.count or self.last_capture is None or
                captured_at-self.last_capture>1.25):
            self.count=count
            self.frames=0
        self.last_capture=captured_at
        self.frames+=1
        return self.frames==2


def frame_is_current(frame_epoch, epoch, captured_at, now, captured_game, game):
    return (frame_epoch==epoch and 0<=now-captured_at<=1.25 and game is not None
            and captured_game==game)


class MatchContinuity:
    def __init__(self):
        self.last_time=None
        self.pending=None

    def observe(self, seconds):
        if seconds is None:return False
        # Also detect a quick restart during the opening seconds. A second
        # consistent reading is still required; a missing clock never resets.
        rewind=self.last_time is not None and (seconds<self.last_time-10 or (seconds<=15 and seconds<=self.last_time-3))
        if rewind:
            if self.pending is not None and self.pending<=seconds<=self.pending+10:
                self.last_time=seconds;self.pending=None
                return True
            self.pending=seconds
            return False
        self.pending=None
        self.last_time=seconds if self.last_time is None else max(self.last_time,seconds)
        return False
