from dataclasses import dataclass
from typing import Optional

import numpy as np

from simulator import Simulator
from pose import Pose


# (1) dataclasses simplifies boilerplate.
@dataclass
class JointConfigurationGoal:
    q: np.ndarray
    start_time: float
    threshold: float = 0.001
    timeout: Optional[float] = None

    def is_timed_out(self, time: float) -> bool:
        # (2) Type hints warns us to check if self.timeout is None.
        if self.timeout is None:
            return False
        return time > self.start_time + self.timeout

    def is_converged(self, q_current: np.ndarray) -> bool:
        q_err = q_current - self.q
        return (np.abs(q_err) < self.threshold).all()


class Robot:
    def __init__(self, simulator: Simulator, urdf: str):
        self._simulator = simulator
        self._uid = simulator.add_body(urdf)
        # (3) Using optionals provides a type-safe way of using nullable values.
        self._q_goal: Optional[JointConfigurationGoal] = None

    @property
    def simulator(self) -> Simulator:
        return self._simulator

    @property
    def uid(self) -> int:
        return self._uid

    def joint_configuration(self) -> np.ndarray:
        return self.simulator.joint_positions(self.uid)

    def set_joint_configuration_goal(
        self, q: np.ndarray, timeout: float = 15.0, threshold: float = 0.001
    ) -> None:
        self._q_goal = JointConfigurationGoal(
            q, threshold=threshold, start_time=self.simulator.time(), timeout=timeout
        )

    def set_pose_goal(
        self, pose: Pose, link_id: int = -1, timeout: float = 15.0, threshold: float = 0.001
    ) -> None:
        self._q_goal = JointConfigurationGoal(
            self.simulator.compute_inverse_kinematics(link_id, pose),
            threshold=threshold,
            start_time=self.simulator.time(),
            timeout=timeout,
        )

    def update_control(self) -> None:
        if self._q_goal is None:
            return

        if self._q_goal.is_timed_out(
            self.simulator.time()
        ) or self._q_goal.is_converged(self.joint_configuration()):
            # (4) The only places where self._q_goal is modified are here and in
            # the self.set_*_goal() functions. Now it's a lot easier to follow
            # what's happening to the mutable state.
            self._q_goal = None
            return

        self.simulator.position_control(
            self.uid,
            target_positions=self._q_goal.q,
        )

    def is_done(self) -> bool:
        return self._q_goal is None


if __name__ == "__main__":
    simulator = Simulator()
    robot = Robot(simulator, "franka_panda.urdf")

    pose = Pose(position=np.array([0.4, 0.0, 0.4]))
    robot.set_pose_goal(pose)
    while not robot.is_done():
        robot.update_control()
        simulator.step()
