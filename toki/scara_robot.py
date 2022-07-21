"""Built upon Brent's Scara robot to include tips from functional programming.

The main changes are:

- The addition of two types of goals (joint/pose).

- The ability to set new goals with `self.set_goal()`. There are two bugs
  introduced with this function.

(1) Typing

    The current implementation has two member variables,
    `self.joint_position_goal` and `self.pose_goal`, although only one can be
    set at a time. This results in error-prone if/else checks to see which goal
    is set.

    Solution:

    Let typing enforce this logic. We can can remove the need for individual
    checks with one `self.goal: Union[JointPositionGoal, PoseGoal]` variable.
    This could be implemented as a literal union or a Goal base class with two
    subclasses.

(2) Pure functions

    If `self.prev_error` doesn't get reset properly when `self.set_goal()` is
    called, then there could be some strange behavior leftover from the previous
    goal, or worse, a runtime error because the dimensions aren't compatible
    with the new goal type.

    Solution:

    Side effects like this can be tricky to catch/keep track of. One extreme is
    to make functions as pure as possible, e.g., having the user hold the
    mutable state. An easier solution might be to consolidate side effects. In
    this case, since prev_error is associated with the goal, it makes sense to
    group them into one object.

"""
import argparse
from dataclasses import dataclass
from typing import Optional

import matplotlib.pyplot as plt
import numpy as np

from simulator import ScaraRobotSimulator


@dataclass
class PdGains:
    kp: float
    kd: float


class ScaraRobotController:
    def __init__(
        self,
        simulator: ScaraRobotSimulator,
        pd_gains: PdGains,
        joint_position_goal: Optional[np.ndarray] = None,
        pose_goal: Optional[np.ndarray] = None,
    ):
        self.simulator = simulator
        self.pd_gains = pd_gains
        self.joint_position_goal = joint_position_goal
        self.pose_goal = pose_goal
        self.prev_error = 0.0

    def set_goal(
        self,
        joint_position_goal: Optional[np.ndarray] = None,
        pose_goal: Optional[np.ndarray] = None,
    ) -> None:
        """Sets a new joint position or pose goal."""
        if joint_position_goal is not None:
            self.joint_position_goal = joint_position_goal
        elif pose_goal is not None:
            self.pose_goal = pose_goal
            # (1) There's a bug here if we don't clear joint_position_goal as well.

        # (2) Another bug where prev_error isn't reset.

    def update_control(self) -> None:
        """Compute PD control output and pass it to the simulator."""
        kp = self.pd_gains.kp
        kd = self.pd_gains.kd

        if self.joint_position_goal is not None:
            error = self.joint_position_goal - self.simulator.get_joint_positions()
            error_delta = error - self.prev_error
            torques = kp * error + kd * error_delta
        elif self.pose_goal is not None:
            error = self.pose_goal - self.simulator.get_xy_position()
            error_delta = error - self.prev_error
            forces = kp * error + kd * error_delta
            torques = self.simulator.get_jacobian().T @ forces

        self.simulator.set_joint_torques(torques)
        self.prev_error = error

    def is_done(self) -> bool:
        """Returns True if the goal is reached."""
        error_norm = np.linalg.norm(
            self.joint_position_goal - self.simulator.get_joint_positions()
        )
        return bool(error_norm < 1e-5)


def run_experiment_and_plot(
    simulator: ScaraRobotSimulator, controller: ScaraRobotController
) -> None:
    # Run our controller, recording the joint state at each step.
    joint_history = []
    while not controller.is_done():
        # Compute torque output and step.
        controller.update_control()
        simulator.step()

        # Record state.
        joint_history.append(simulator.get_joint_positions())

    # Plot history of joint angles.
    for i, qs in enumerate(np.array(joint_history).T):
        plt.plot(range(len(qs)), qs, label=f"qs{i}")
    plt.title(f"Converged in {simulator.get_simulation_time()} seconds")
    plt.legend()
    plt.show()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--kp", type=float, help="P gain.", default=10.0)
    parser.add_argument("--kd", type=float, help="D gain.", default=0.30)
    args = parser.parse_args()

    # Get control gains from argument parser.
    pd_gains = PdGains(kp=args.kp, kd=args.kd)

    # Create our simulator and robot.
    simulator = ScaraRobotSimulator()
    controller = ScaraRobotController(
        simulator, joint_position_goal=[0.5, -0.2, 0.3], pd_gains=pd_gains
    )
    run_experiment_and_plot(simulator, controller)
