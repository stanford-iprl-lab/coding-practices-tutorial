from dataclasses import dataclass

import numpy as np


@dataclass
class Pose:
    position: np.ndarray = np.zeros(3)
    quaternion: np.ndarray = np.array([0.0, 0.0, 0.0, 1.0])
