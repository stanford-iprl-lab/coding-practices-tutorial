from dataclasses import dataclass
from typing import Optional

import numpy as np

from simulator import Simulator
from pose import Pose


@dataclass
class JointConfigurationGoal:
    q: np.ndarray
    start_time: float
    threshold: float = 0.001
    timeout: Optional[float] = None

    def is_timed_out(self, time: float) -> bool:
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

    @property
    def simulator(self) -> Simulator:
        return self._simulator

    @property
    def uid(self) -> int:
        return self._uid

    def joint_configuration(self) -> np.ndarray:
        return self.simulator.joint_positions(self.uid)

    def compute_pose_goal(
        self,
        pose: Pose,
        link_id: int = -1,
        timeout: float = 15.0,
        threshold: float = 0.001,
    ) -> JointConfigurationGoal:
        return JointConfigurationGoal(
            self.simulator.compute_inverse_kinematics(link_id, pose),
            threshold=threshold,
            start_time=self.simulator.time(),
            timeout=timeout,
        )

    def update_control(self, goal: JointConfigurationGoal) -> None:
        self.simulator.position_control(
            self.uid,
            target_positions=goal.q,
        )

    def is_done(self, goal: JointConfigurationGoal) -> bool:
        return goal.is_timed_out(self.simulator.time()) or goal.is_converged(
            self.joint_configuration()
        )


if __name__ == "__main__":
    simulator = Simulator()
    robot = Robot(simulator, "franka_panda.urdf")

    pose = Pose(position=np.array([0.4, 0.0, 0.4]))
    # (4) By making the user hold onto the goal and pass it into this
    # function, we can make the Robot class completely stateless. It's now easy
    # to see how data flows between functions by the inputs/outputs of function
    # calls. Apart from allowing a more concise Robot implementation, it leaves
    # less room for potential bugs. For example, `robot.update_control()` cannot
    # be accidentally called out of order, because it needs the output of
    # `robot.compute_pose_goal()`.
    goal = robot.compute_pose_goal(pose)
    while not robot.is_done(goal):
        robot.update_control(goal)
        # (4) There's still some hidden state being passed from the robot to the
        # simulator (control commands). This makes sense for a module as complex
        # as a simulator. Implementing pure functions isn't always the best
        # approach since it could make the API too cumbersome.
        simulator.step()
