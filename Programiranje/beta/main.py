# main.py
import multiprocessing

# Use the 'spawn' start method to avoid fork-related issues when launching
# child processes from a Qt GUI. This prevents duplicated state and unexpected
# child behavior when using multiprocessing.
try:
    multiprocessing.set_start_method('spawn', force=True)
except RuntimeError:
    # If the start method is already set elsewhere, ignore.
    pass

from gui import run_gui

if __name__ == "__main__":
    run_gui()
