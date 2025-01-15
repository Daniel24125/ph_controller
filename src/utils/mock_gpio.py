# mock_gpio.py

class MockGPIO:
    # GPIO Modes
    BOARD = "BOARD"
    BCM = "BCM"
    
    # GPIO States
    HIGH = 1
    LOW = 0
    
    # GPIO Directions
    OUT = "OUT"
    IN = "IN"
    
    # Pull up/down
    PUD_UP = "PUD_UP"
    PUD_DOWN = "PUD_DOWN"
    
    # Edge detection
    RISING = "RISING"
    FALLING = "FALLING"
    BOTH = "BOTH"
    
    def __init__(self):
        self._mode = None
        self._pin_states = {}
        self._pin_modes = {}
        self._event_callbacks = {}
        self._warnings = True
        print("Mock GPIO Initialized")
    
    def setmode(self, mode):
        """Set the pin numbering mode."""
        self._mode = mode
        print(f"GPIO Mode set to: {mode}")
    
    def getmode(self):
        """Get the current pin numbering mode."""
        return self._mode
    
    def setup(self, channel, direction, pull_up_down=None, initial=None):
        """Setup GPIO channel."""
        if isinstance(channel, (list, tuple)):
            for ch in channel:
                self._setup_single_channel(ch, direction, pull_up_down, initial)
        else:
            self._setup_single_channel(channel, direction, pull_up_down, initial)
    
    def _setup_single_channel(self, channel, direction, pull_up_down=None, initial=None):
        """Setup a single GPIO channel."""
        self._pin_modes[channel] = direction
        if direction == self.OUT:
            self._pin_states[channel] = initial if initial is not None else self.LOW
        elif direction == self.IN:
            if pull_up_down == self.PUD_UP:
                self._pin_states[channel] = self.HIGH
            else:
                self._pin_states[channel] = self.LOW
        print(f"Setup GPIO {channel} as {direction}")
    
    def output(self, channel, state):
        """Set output state of GPIO channel(s)."""
        if isinstance(channel, (list, tuple)):
            for ch, st in zip(channel, state if isinstance(state, (list, tuple)) else [state] * len(channel)):
                self._output_single_channel(ch, st)
        else:
            self._output_single_channel(channel, state)
    
    def _output_single_channel(self, channel, state):
        """Set output state of a single GPIO channel."""
        if channel not in self._pin_modes:
            raise RuntimeError(f"GPIO {channel} not setup")
        if self._pin_modes[channel] != self.OUT:
            raise RuntimeError(f"GPIO {channel} not setup as OUTPUT")
        
        self._pin_states[channel] = state
        print(f"GPIO {channel} set to {state}")
        
        # Trigger event callbacks if any
        self._check_events(channel)
    
    def input(self, channel):
        """Read input value from GPIO channel."""
        if channel not in self._pin_modes:
            raise RuntimeError(f"GPIO {channel} not setup")
        return self._pin_states.get(channel, self.LOW)
    
    def cleanup(self, channel=None):
        """Clean up GPIO channels."""
        if channel is None:
            self._pin_states.clear()
            self._pin_modes.clear()
            self._event_callbacks.clear()
            print("Cleaned up all GPIO channels")
        else:
            channels = [channel] if isinstance(channel, int) else channel
            for ch in channels:
                self._pin_states.pop(ch, None)
                self._pin_modes.pop(ch, None)
                self._event_callbacks.pop(ch, None)
                print(f"Cleaned up GPIO {ch}")
    
    def add_event_detect(self, channel, edge, callback=None, bouncetime=None):
        """Add interrupt event detection."""
        if channel not in self._pin_modes:
            raise RuntimeError(f"GPIO {channel} not setup")
        self._event_callbacks[channel] = {
            'edge': edge,
            'callback': callback,
            'bouncetime': bouncetime
        }
        print(f"Added {edge} event detection on GPIO {channel}")
    
    def remove_event_detect(self, channel):
        """Remove interrupt event detection."""
        self._event_callbacks.pop(channel, None)
        print(f"Removed event detection from GPIO {channel}")
    
    def event_detected(self, channel):
        """Returns True if an event was detected since the last call."""
        return False  # Mock implementation
    
    def add_event_callback(self, channel, callback):
        """Add a callback for an event already defined using add_event_detect()."""
        if channel in self._event_callbacks:
            self._event_callbacks[channel]['callback'] = callback
    
    def wait_for_edge(self, channel, edge, timeout=None):
        """Wait for an edge event."""
        print(f"Waiting for {edge} edge on GPIO {channel}")
        return None  # Mock implementation
    
    def setwarnings(self, state):
        """Enable or disable warning messages."""
        self._warnings = state
    
    def _check_events(self, channel):
        """Internal method to check and trigger events."""
        if channel in self._event_callbacks and self._event_callbacks[channel]['callback']:
            event = self._event_callbacks[channel]
            current_state = self._pin_states[channel]
            
            if (event['edge'] == self.RISING and current_state == self.HIGH) or \
               (event['edge'] == self.FALLING and current_state == self.LOW) or \
               (event['edge'] == self.BOTH):
                event['callback'](channel)