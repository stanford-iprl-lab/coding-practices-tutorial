#!/usr/bin/env python3

"""Built upon Brent's Scara robot to include tips from functional programming.

The main changes are:

- The addition of two types of goals (joint/pose).

- The ability to set new goals with `self.set_goal()`. There are two bugs
  introduced with this function.

(1) Typing

    The current implementation has two member variables,
    `self.joint_position_goal` and `self.ee_position_goal`, although only one
    can be set at a time. This results in error-prone if/else checks to see
    which goal is set.

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
import time
from typing import Optional

import numpy as np

from simulator import RobotSimulator
from redisgl.server import WebServer


@dataclass
class PdGains:
    kp: float
    kd: float


class RobotController:
    def __init__(
        self,
        simulator: RobotSimulator,
        pd_gains: PdGains,
        joint_position_goal: Optional[np.ndarray] = None,
        ee_position_goal: Optional[np.ndarray] = None,
    ):
        self.simulator = simulator
        self.pd_gains = pd_gains
        self.joint_position_goal = joint_position_goal
        self.ee_position_goal = ee_position_goal
        self.error: Optional[np.ndarray] = None

    def set_goal(
        self,
        joint_position_goal: Optional[np.ndarray] = None,
        ee_position_goal: Optional[np.ndarray] = None,
    ) -> None:
        """Sets a new joint position or pose goal."""
        if joint_position_goal is not None:
            self.joint_position_goal = joint_position_goal
        elif ee_position_goal is not None:
            self.ee_position_goal = ee_position_goal
            # (1) There's a bug here if we don't clear joint_position_goal as well.

        # (2) Another bug where prev_error isn't reset.

    def update_control(self) -> None:
        """Compute PD control output and pass it to the simulator."""
        kp = self.pd_gains.kp
        kd = self.pd_gains.kd

        if self.joint_position_goal is not None:
            error = self.joint_position_goal - self.simulator.get_joint_positions()
            velocity = self.simulator.get_joint_velocities()
            joint_accelerations = kp * error - kd * velocity
            self.simulator.set_joint_accelerations(joint_accelerations)
        elif self.ee_position_goal is not None:
            error = self.ee_position_goal - self.simulator.get_ee_position()
            velocity = self.simulator.get_ee_velocity()
            acceleration = kp * error - kd * velocity
            self.simulator.set_ee_acceleration(acceleration)

        self.error = error

    def is_done(self) -> bool:
        """Returns True if the goal is reached."""
        if self.error is None:
            return False

        error_norm = np.linalg.norm(self.error)
        return bool(error_norm < 1e-5)


def run_controller(
    simulator: RobotSimulator,
    controller: RobotController,
    server: WebServer,
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
    # for i, qs in enumerate(np.array(joint_history).T):
    #     plt.plot(range(len(qs)), qs, label=f"qs{i}")
    # plt.title(f"Converged in {simulator.get_simulation_time()} seconds")
    # plt.legend()
    # plt.show()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--kp", type=float, help="P gain.", default=49.0)
    parser.add_argument("--kd", type=float, help="D gain.", default=14.0)
    args = parser.parse_args()

    # Get control gains from argument parser.
    pd_gains = PdGains(kp=args.kp, kd=args.kd)

    # Initialize the web server and simulator.
    server = WebServer()
    simulator = RobotSimulator(server)

    # Joint position control.
    joint_position_goal = np.array([-0.4, 0.1, -0.7, -1.5, 0.0, 1.6, -0.3])
    controller = RobotController(
        simulator, joint_position_goal=joint_position_goal, pd_gains=pd_gains
    )

    # Operational space control.
    # controller = RobotController(
    #     simulator, ee_position_goal=np.array([0.3, -0.5, 0.5]), pd_gains=pd_gains
    # )

    # Run the server and controller.
    server.on_ready(lambda: run_controller(simulator, controller, server))
    server.connect(http_port=8000, ws_port=8001)
    server.wait()
