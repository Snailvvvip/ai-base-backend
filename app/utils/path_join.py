import os
from typing import List


def path_join(*pat_list: List[str]):
  return os.path.join(*pat_list).replace('\\', '/')
