import logging
import inspect
import os
from configs import DEBUGGING
    
frame = inspect.currentframe()
filename = frame.f_code.co_filename
short_filename = os.path.basename(filename)

debugging_portion = f"{short_filename} - {frame.f_lineno}" if DEBUGGING else ""

logging.basicConfig(
    level=logging.INFO,
    format=f'{debugging_portion} \n %(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)