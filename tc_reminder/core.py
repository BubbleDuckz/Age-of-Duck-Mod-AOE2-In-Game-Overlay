"""Conservative reminder state machine; no Windows or vision dependencies."""
from dataclasses import dataclass


@dataclass
class Observation:
    busy: int = 0
    selected_tcs: int | None = None
    selection_verified: bool = False
    foreground: bool = False
    gameplay: bool = False
    paused: bool = False
    advancing: bool = False
    confident: bool = False
    housed: bool = False
    session: str = ""
    reason: str = "Waiting for a confident gameplay frame"


class Reminder:
    def __init__(self):
        self.total = None
        self.learned_at = None
        self.session = None
        self.shortfall_since = None
        self.last_cue = float('-inf')

    def forget(self):
        self.__init__()

    def step(self, obs, now, cooldown=1, validated=False):
        if obs.session and obs.session != self.session:
            self.forget()
            self.session = obs.session
        safe = obs.foreground and obs.gameplay and obs.advancing and obs.confident
        count_safe = obs.foreground and (obs.paused or (obs.gameplay and obs.advancing))
        if count_safe and obs.selection_verified and obs.selected_tcs is not None and obs.selected_tcs >= 1 and (self.total is None or obs.selected_tcs > 1):
            self.total = obs.selected_tcs
            self.learned_at = now
        if not safe:
            self.shortfall_since = None
            return '', False, obs.reason
        if self.total is None:
            self.shortfall_since = None
            return '', False, 'TC total unknown — select a TC in the game'
        if obs.housed:
            self.shortfall_since = None
            return ('Population blocked' if validated else ''), False, 'Housed queues: separate from a possible queue shortfall'
        if obs.busy >= self.total:
            self.shortfall_since = None
            return '', False, 'Enough TCs appear busy'
        if self.shortfall_since is None:
            self.shortfall_since = now
        if now - self.shortfall_since < 3:
            return '', False, 'Waiting for a 3-second persistent shortfall'
        if not validated:
            return '', False, 'Possible shortfall — alerts locked pending independent screenshot validation'
        cue = now - self.last_cue >= max(1, cooldown)
        if cue:
            self.last_cue = now
        return 'Check TC queues', cue, 'Possible queue shortfall; remembered count may be stale'
