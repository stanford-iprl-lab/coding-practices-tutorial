"""Simple physics simulator for a 3 degree-of-freedom SCARA robot.

For the sake of this tutorial, we'll consider this as fixed, and focus on how we can
improve `robot.py`!"""

import numpy as np
import numpy.typing as npt


class ScaraRobotSimulator:
    ITERS_PER_SEC = 50.0

    def __init__(self):
        self.num_iters = 0
        self.joint_positions = np.array([0.0, 0.0, 0.0])
        self.joint_velocities = np.array([0.0, 0.0, 0.0])
        self.joint_torques = np.array([0.0, 0.0, 0.0])

    def step(self) -> None:
        """Take one physics simulation step."""
        self.joint_positions += self.joint_velocities / self.ITERS_PER_SEC
        self.joint_velocities = (
            # Friction losses.
            self.joint_velocities
            * 0.98
        ) + self.joint_torques * np.array([1e-3, 1e-2, 5e-3])
        self.num_iters += 1

    def get_simulation_time(self) -> float:
        """Get the current simulation time, in seconds."""
        return self.num_iters / self.ITERS_PER_SEC

    def get_joint_positions(self) -> npt.NDArray[np.float64]:
        """Get joint positions for our robot."""
        return self.joint_positions.copy()

    def set_joint_torques(self, torques: npt.NDArray[np.float64]) -> None:
        """Set joint torques for our robot."""
        assert (
            torques.shape
            == self.joint_velocities.shape
            == self.joint_positions.shape
            == (3,)
        )
        self.joint_torques = torques
