import numpy as np

from pose import Pose


class Simulator:
    def __init__(self):
        self._num_iters = 0

    def add_body(self, urdf: str) -> int:
        return 0

    def time(self) -> float:
        return self._num_iters / 1.0

    def step(self) -> None:
        self._num_iters += 1

    def compute_inverse_kinematics(self, link_id: int, pose: Pose) -> np.ndarray:
        return np.zeros(7)

    def joint_positions(self, uid: int) -> np.ndarray:
        return np.ones(7)

    def position_control(self, uid: int, target_positions: np.ndarray) -> None:
        print(f"Position control {self._num_iters}")
