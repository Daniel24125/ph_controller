import os
import datetime
import traceback
import sys
import glob
from typing import Optional, List, Tuple
from pathlib import Path
import sys 

sys.path.append(str(Path(__file__).parent.parent))

from utils.logger import logger

class ErrorLogger:
    """
    A logger class that saves error information to a log file whenever an error occurs
    and manages log storage space.
    """
    
    def __init__(self, 
                 log_directory: str, 
                 log_file_name: Optional[str] = None,
                 max_log_files: int = 100,
                 max_log_age_days: int = 30,
                 max_total_size_mb: int = 100):
        """
        Initialize the logger with a directory to save log files.
        
        Args:
            log_directory: Directory path where log files will be stored
            log_file_name: Name of the log file (if None, a timestamp-based name will be used)
            max_log_files: Maximum number of log files to keep
            max_log_age_days: Maximum age of log files in days
            max_total_size_mb: Maximum total size of all log files in MB
        """
        # Create the log directory if it doesn't exist
        os.makedirs(log_directory, exist_ok=True)
        
        self.log_directory = log_directory
        self.log_file_name = log_file_name or f"error_log_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        self.log_file_path = os.path.join(log_directory, self.log_file_name)
        
        # Storage management settings
        self.max_log_files = max_log_files
        self.max_log_age_days = max_log_age_days
        self.max_total_size_mb = max_total_size_mb
        
    def log_error(self, error: Exception , additional_info: str = ""):
        """
        Log an error to the file with timestamp, error type, message, and traceback.
        Also manages log storage.
        
        Args:
            error: The exception object to log
            additional_info: Any additional information to include in the log
        """
        logger.info("Saving the error into a log file...")
        # First, manage storage to ensure we have space
        self.manage_log_storage()
        
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        error_type = type(error).__name__
        error_message = str(error)
        
        # Get the full traceback
        tb = traceback.format_exc()
        
        # Format the log entry
        log_entry = (
            f"===== ERROR LOG: {timestamp} =====\n"
            f"Type: {error_type}\n"
            f"Message: {error_message}\n"
        )
        
        if additional_info:
            log_entry += f"Additional Info: {additional_info}\n"
            
        log_entry += f"Traceback:\n{tb}\n\n"
        
        # Write to log file
        with open(self.log_file_path, 'a') as log_file:
            log_file.write(log_entry)
            
        return log_entry
    
    def manage_log_storage(self):
        """
        Manage log storage by enforcing maximum number of files, 
        maximum age, and maximum total size constraints.
        """
        # Get all log files with their stats
        log_files = self._get_log_files_with_stats()
        
        # Apply constraints in order of priority
        # 1. Remove old files beyond max age
        self._remove_old_logs(log_files)
        
        # Re-scan log files after age-based cleanup
        log_files = self._get_log_files_with_stats()
        
        # 2. Remove files if total size exceeds max
        self._enforce_max_size(log_files)
        
        # Re-scan log files after size-based cleanup
        log_files = self._get_log_files_with_stats()
        
        # 3. Remove excess files beyond max count
        self._enforce_max_files(log_files)
    
    def _get_log_files_with_stats(self) -> List[Tuple[str, float, datetime.datetime]]:
        """
        Get list of log files with their stats (path, size, creation time).
        
        Returns:
            List of tuples containing (file_path, size_in_mb, creation_time)
        """
        log_files = []
        for file_path in glob.glob(os.path.join(self.log_directory, "*.log")):
            # Skip the current log file
            if os.path.abspath(file_path) == os.path.abspath(self.log_file_path):
                continue
                
            # Get file stats
            stats = os.stat(file_path)
            size_mb = stats.st_size / (1024 * 1024)  # Convert bytes to MB
            creation_time = datetime.datetime.fromtimestamp(stats.st_birthtime )
            
            log_files.append((file_path, size_mb, creation_time))
            
        # Sort by creation time (oldest first)
        return sorted(log_files, key=lambda x: x[2])
    
    def _remove_old_logs(self, log_files: List[Tuple[str, float, datetime.datetime]]):
        """
        Remove log files older than max_log_age_days.
        
        Args:
            log_files: List of tuples containing (file_path, size_in_mb, creation_time)
        """
        now = datetime.datetime.now()
        max_age = datetime.timedelta(days=self.max_log_age_days)
        
        for file_path, _, creation_time in log_files:
            if now - creation_time > max_age:
                try:
                    os.remove(file_path)
                except OSError:
                    pass  # Failed to remove file, just continue
    
    def _enforce_max_size(self, log_files: List[Tuple[str, float, datetime.datetime]]):
        """
        Remove oldest log files if total size exceeds max_total_size_mb.
        
        Args:
            log_files: List of tuples containing (file_path, size_in_mb, creation_time)
        """
        # Calculate total size
        total_size_mb = sum(size for _, size, _ in log_files)
        
        # Remove oldest files until we're under the limit
        for file_path, size_mb, _ in log_files:
            if total_size_mb <= self.max_total_size_mb:
                break
                
            try:
                os.remove(file_path)
                total_size_mb -= size_mb
            except OSError:
                pass  # Failed to remove file, just continue
    
    def _enforce_max_files(self, log_files: List[Tuple[str, float, datetime.datetime]]):
        """
        Remove oldest log files if count exceeds max_log_files.
        
        Args:
            log_files: List of tuples containing (file_path, size_in_mb, creation_time)
        """
        # Remove oldest files until we're under the limit
        files_to_remove = max(0, len(log_files) - self.max_log_files)
        
        for i in range(files_to_remove):
            if i < len(log_files):
                try:
                    os.remove(log_files[i][0])
                except OSError:
                    pass  # Failed to remove file, just continue
    
    def __call__(self, error: Exception, additional_info: str = ""):
        """
        Make the logger instance callable to quickly log errors.
        
        Args:
            error: The exception object to log
            additional_info: Any additional information to include in the log
        """
        return self.log_error(error, additional_info)
    
    @staticmethod
    def exception_handler(logger, additional_info: str = ""):
        """
        Create an exception handler function to be used with sys.excepthook
        
        Args:
            logger: Logger instance to use for logging
            additional_info: Any additional information to include in the log
            
        Returns:
            Exception handler function
        """
        def handle_exception(exc_type, exc_value, exc_traceback):
            # Log the error
            logger.log_error(exc_value, additional_info)
            
            # Print to stderr as usual
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            
        return handle_exception
    
    def set_as_global_exception_handler(self, additional_info: str = ""):
        """
        Set this logger as the global exception handler.
        
        Args:
            additional_info: Any additional information to include in all logs
        """
        sys.excepthook = self.exception_handler(self, additional_info)

if __name__ == "__main__": 
    error_logger = ErrorLogger("src/logs",None, 100,30)
    try:
        result = 10 / 0
    except Exception as e:
        error_logger.log_error(e)
