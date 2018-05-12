"""Mixer that controls volume using a Yamaha receiver."""

from __future__ import unicode_literals

import logging

from mopidy import mixer
from mopidy import core

import pykka

from mopidy_yamaha import talker


logger = logging.getLogger(__name__)


class YamahaTalkerSingleton:
    yamaha_talker = None

    @classmethod
    def start_yamaha_talker(cls, host, source, party_mode):
        if cls.yamaha_talker is None:
            cls.yamaha_talker = talker.YamahaTalker.start(
                host=host,
                source=source,
                party_mode=party_mode,
            )
        return cls.yamaha_talker.proxy()

class YamahaFrontend(pykka.ThreadingActor, core.CoreListener):
    def __init__(self, config, core):
        super(YamahaFrontend, self).__init__(config, core)

        self.host = config['yamaha']['host']
        self.source = config['yamaha']['source']
        self.party_mode = config['yamaha']['party_mode']

        self._yamaha_talker = None
        
    def on_start(self):
        self._yamaha_talker = YamahaTalkerSingleton.start_yamaha_talker(self.host, self.source, self.party_mode)

    def playback_state_changed(self, old_state, new_state):
        if new_state == core.PlaybackState.PLAYING:
            self._yamaha_talker.start_playback()

class YamahaMixer(pykka.ThreadingActor, mixer.Mixer):

    name = 'yamaha'

    def __init__(self, config):
        super(YamahaMixer, self).__init__(config)

        self.host = config['yamaha']['host']
        self.source = config['yamaha']['source']
        self.party_mode = config['yamaha']['party_mode']

        self._previous_volume = None
        self._previous_mute = None
        self._yamaha_talker = None

    def get_volume(self):
        volume, mute = self._yamaha_talker.get_volume_mute().get()
        if self._previous_volume != volume:
            self.trigger_volume_changed(volume)
        self._previous_volume = volume
        if self._previous_mute != mute:
            self.trigger_mute_changed(mute)
        self._previous_mute = mute
        return volume
            

    def set_volume(self, volume):
        self._yamaha_talker.set_volume(volume)
        self.trigger_volume_changed(volume)
        return True

    def get_mute(self):
        if self._previous_mute is None:
            self.get_volume()
        return self._previous_mute

    def set_mute(self, mute):
        self._yamaha_talker.set_mute(mute)
        self.trigger_mute_changed(mute)

    def on_start(self):
        self._yamaha_talker = YamahaTalkerSingleton.start_yamaha_talker(self.host, self.source, self.party_mode)

