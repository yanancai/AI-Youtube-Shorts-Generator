"""
Error handling utilities for suppressing common library warnings and errors
"""
import warnings
import sys
import os
from contextlib import contextmanager

def suppress_tqdm_errors():
    """Suppress tqdm AttributeError warnings that occur during cleanup"""
    import tqdm
    
    # Store original del method
    original_del = tqdm.tqdm.__del__
    
    def safe_del(self):
        try:
            original_del(self)
        except (AttributeError, KeyError):
            # Silently ignore tqdm cleanup errors
            pass
    
    # Replace with safe version
    tqdm.tqdm.__del__ = safe_del

def suppress_broken_pipe_errors():
    """Handle broken pipe errors when output is piped to head, tail, etc."""
    def handle_broken_pipe(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except BrokenPipeError:
                # Python flushes standard streams on exit; redirect remaining output
                # to devnull to avoid another BrokenPipeError at shutdown
                devnull = os.open(os.devnull, os.O_WRONLY)
                os.dup2(devnull, sys.stdout.fileno())
                sys.exit(1)  # Python exits with error code 1 on EPIPE
        return wrapper
    return handle_broken_pipe

@contextmanager
def suppress_stdout_stderr():
    """Context manager to suppress stdout/stderr output"""
    with open(os.devnull, "w") as devnull:
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        try:
            sys.stdout = devnull
            sys.stderr = devnull
            yield
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr

def handle_broken_pipe():
    """Handle broken pipe by redirecting output to devnull"""
    devnull = os.open(os.devnull, os.O_WRONLY)
    os.dup2(devnull, sys.stdout.fileno())

def setup_error_handling():
    """Setup all error handling and warning suppression"""
    # Suppress tqdm cleanup errors
    suppress_tqdm_errors()
    
    # Suppress specific warnings that aren't critical
    warnings.filterwarnings("ignore", category=UserWarning, module="torch")
    warnings.filterwarnings("ignore", category=FutureWarning, module="torch")
    warnings.filterwarnings("ignore", category=UserWarning, module="transformers")
    
    # Handle broken pipe in main print functions
    original_print = print
    def safe_print(*args, **kwargs):
        try:
            original_print(*args, **kwargs)
        except BrokenPipeError:
            devnull = os.open(os.devnull, os.O_WRONLY)
            os.dup2(devnull, sys.stdout.fileno())
            sys.exit(1)
    
    # Don't actually replace print as it might cause other issues
    # Just setup the tqdm handling which is the main culprit

if __name__ == "__main__":
    # Test the error handling
    setup_error_handling()
    print("Error handling setup complete")
