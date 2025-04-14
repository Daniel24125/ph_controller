# mock_lgpio.py

class MockLGPIO:
    # Constants
    # GPIO modes
    INPUT = 0
    OUTPUT = 1
    ALT0 = 2
    ALT1 = 3
    ALT2 = 4
    ALT3 = 5
    ALT4 = 6
    ALT5 = 7
    
    # Pull up/down resistors
    SET_PULL_NONE = 0
    SET_PULL_UP = 1
    SET_PULL_DOWN = 2
    
    # Edge detection
    RISING_EDGE = 0
    FALLING_EDGE = 1
    BOTH_EDGES = 2
    
    # GPIO levels
    LOW = 0
    HIGH = 1
    
    # Alert options
    ALERT_FUNC = 0
    
    def __init__(self):
        self._handles = {}  # Store chip handles
        self._pin_states = {}  # Store pin states
        self._pin_modes = {}  # Store pin modes
        self._alerts = {}  # Store alert callbacks
        self._chip_count = 0  # Counter for chip handles
        print("Mock LGPIO Initialized")
    
    # Chip handling functions
    def gpiochip_open(self, gpiochip=0):
        """Open a GPIO chip and return a handle."""
        handle = self._chip_count
        self._chip_count += 1
        self._handles[handle] = {
            'chip': gpiochip,
            'pins': {}
        }
        print(f"Opened GPIO chip {gpiochip}, handle: {handle}")
        return handle
    
    def gpiochip_close(self, handle):
        """Close a GPIO chip."""
        if handle in self._handles:
            self._handles.pop(handle)
            print(f"Closed GPIO chip handle: {handle}")
            return 0
        return -1
    
    # GPIO configuration functions
    def gpio_claim_output(self, handle, gpio, level=0):
        """Claim a GPIO for output."""
        if handle not in self._handles:
            return -1
        
        self._handles[handle]['pins'][gpio] = {
            'mode': self.OUTPUT,
            'level': level
        }
        self._pin_modes[(handle, gpio)] = self.OUTPUT
        self._pin_states[(handle, gpio)] = level
        print(f"Claimed GPIO {gpio} for output, initial level: {level}")
        return 0
    
    def gpio_claim_input(self, handle, gpio):
        """Claim a GPIO for input."""
        if handle not in self._handles:
            return -1
        
        self._handles[handle]['pins'][gpio] = {
            'mode': self.INPUT,
            'level': 0
        }
        self._pin_modes[(handle, gpio)] = self.INPUT
        self._pin_states[(handle, gpio)] = 0
        print(f"Claimed GPIO {gpio} for input")
        return 0
    
    def gpio_free(self, handle, gpio):
        """Free a GPIO."""
        if handle in self._handles and gpio in self._handles[handle]['pins']:
            self._handles[handle]['pins'].pop(gpio)
            self._pin_modes.pop((handle, gpio), None)
            self._pin_states.pop((handle, gpio), None)
            self._alerts.pop((handle, gpio), None)
            print(f"Freed GPIO {gpio}")
            return 0
        return -1
    
    # I/O functions
    def gpio_write(self, handle, gpio, level):
        """Write to a GPIO."""
        if handle not in self._handles or gpio not in self._handles[handle]['pins']:
            return -1
        
        if self._pin_modes.get((handle, gpio)) != self.OUTPUT:
            print(f"Error: GPIO {gpio} not configured as output")
            return -1
        
        self._pin_states[(handle, gpio)] = level
        print(f"Wrote level {level} to GPIO {gpio}")
        
        # Trigger alert callbacks if any
        self._check_alerts(handle, gpio)
        return 0
    
    def gpio_read(self, handle, gpio):
        """Read from a GPIO."""
        if handle not in self._handles or gpio not in self._handles[handle]['pins']:
            return -1
        
        return self._pin_states.get((handle, gpio), 0)
    
    # Pull up/down configuration
    def gpio_set_pull_up_down(self, handle, gpio, pud):
        """Set the GPIO pull up/down resistor."""
        if handle not in self._handles or gpio not in self._handles[handle]['pins']:
            return -1
        
        self._handles[handle]['pins'][gpio]['pud'] = pud
        
        # Adjust pin state based on pull up/down if it's an input
        if self._pin_modes.get((handle, gpio)) == self.INPUT:
            if pud == self.SET_PULL_UP:
                self._pin_states[(handle, gpio)] = 1
            elif pud == self.SET_PULL_DOWN:
                self._pin_states[(handle, gpio)] = 0
                
        print(f"Set pull up/down {pud} for GPIO {gpio}")
        return 0
    
    # Edge detection and alerts
    def gpio_set_alerts(self, handle, gpio, edge, func):
        """Set alerts for GPIO edge events."""
        if handle not in self._handles or gpio not in self._handles[handle]['pins']:
            return -1
        
        self._alerts[(handle, gpio)] = {
            'edge': edge,
            'callback': func
        }
        print(f"Set {self._edge_to_str(edge)} alert for GPIO {gpio}")
        return 0
    
    def _edge_to_str(self, edge):
        """Convert edge constant to string for logging."""
        if edge == self.RISING_EDGE:
            return "RISING_EDGE"
        elif edge == self.FALLING_EDGE:
            return "FALLING_EDGE"
        elif edge == self.BOTH_EDGES:
            return "BOTH_EDGES"
        return "UNKNOWN"
    
    def _check_alerts(self, handle, gpio):
        """Check if alerts should be triggered."""
        if (handle, gpio) not in self._alerts or not self._alerts[(handle, gpio)]['callback']:
            return
        
        alert = self._alerts[(handle, gpio)]
        current_state = self._pin_states[(handle, gpio)]
        
        should_trigger = False
        if alert['edge'] == self.RISING_EDGE and current_state == self.HIGH:
            should_trigger = True
        elif alert['edge'] == self.FALLING_EDGE and current_state == self.LOW:
            should_trigger = True
        elif alert['edge'] == self.BOTH_EDGES:
            should_trigger = True
        
        if should_trigger:
            # In lgpio, callback is typically called with (gpio, level, tick)
            # For mock, we'll use current time in microseconds
            import time
            tick = int(time.time() * 1000000)
            alert['callback'](gpio, current_state, tick)
    
    # Group operations
    def group_claim_output(self, handle, gpio_list, levels=None):
        """Claim a group of GPIOs for output."""
        if levels is None:
            levels = [0] * len(gpio_list)
        
        for i, gpio in enumerate(gpio_list):
            level = levels[i] if i < len(levels) else 0
            self.gpio_claim_output(handle, gpio, level)
        
        print(f"Claimed group of {len(gpio_list)} GPIOs for output")
        return 0
    
    def group_write(self, handle, gpio_list, levels):
        """Write to a group of GPIOs."""
        for i, gpio in enumerate(gpio_list):
            if i < len(levels):
                self.gpio_write(handle, gpio, levels[i])
        
        print(f"Wrote to group of {len(gpio_list)} GPIOs")
        return 0
    
    # Cleanup
    def cleanup(self):
        """Clean up all resources."""
        self._handles.clear()
        self._pin_states.clear()
        self._pin_modes.clear()
        self._alerts.clear()
        self._chip_count = 0
        print("Cleaned up all LGPIO resources")