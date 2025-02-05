import threading
import time

class IntervalTimer:
    def __init__(self):
        self.running = False
        self.thread = None
    
    def start(self, interval, callback):
        print("Starting the Timer")
        self.running = True
        self.thread = threading.Thread(target=self._run_interval, args=(interval, callback))
        self.thread.start()
    
    def stop(self):
        self.running = False
        print("Stopping the Timer")
        if self.thread:
            self.thread.join()
    
    def _run_interval(self, interval, callback):
        while self.running:
            callback()
            time.sleep(interval)

def run_fn():
    print("HELLO")

if __name__ == "__main__": 
    timer = IntervalTimer()
    try:
        timer.start(1, run_fn)
    except KeyboardInterrupt: 
        timer.stop()

