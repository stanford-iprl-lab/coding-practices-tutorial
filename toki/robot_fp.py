#!/usr/bin/env python3

"""Interactive demo code: Part 2

This simulation contains a Franka Panda arm and a box. The arm starts off in its
home configuration, and it needs to reach over and touch the box in the corner.

We will use joint space control to safely position the arm above the box, and
then use Operational space control to bring the end-effector down to touch it.

This code is correctly annotated with types and passes static type checking, but
it still doesn't run correctly. Can you find the bugs?

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

    If `self.error` doesn't get reset properly when `self.set_goal()` is called,
    then there could be some strange behavior leftover from the previous goal.

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

import numpy as np

from simulator import RobotSimulator
from redisgl.server import WebServer


@dataclass
class PdGains:
    kp: float
    kd: float


@dataclass
class Goal:
    goal: np.ndarray
    error: Optional[np.ndarray] = None


class JointPositionGoal(Goal):
    pass


class EePositionGoal(Goal):
    pass


class RobotController:
    def __init__(
        self,
        simulator: RobotSimulator,
        pd_gains: PdGains,
    ):
        self.simulator = simulator
        self.pd_gains = pd_gains

    def update_control(self, goal: Goal) -> None:
        """Compute PD control output and pass it to the simulator."""
        kp = self.pd_gains.kp
        kd = self.pd_gains.kd

        if isinstance(goal, JointPositionGoal):
            error = goal.goal - self.simulator.get_joint_positions()
            velocity = self.simulator.get_joint_velocities()
            joint_accelerations = kp * error - kd * velocity
            self.simulator.set_joint_accelerations(joint_accelerations)
        elif isinstance(goal, EePositionGoal):
            error = goal.goal - self.simulator.get_ee_position()
            velocity = self.simulator.get_ee_velocity()
            ee_acceleration = kp * error - kd * velocity
            self.simulator.set_ee_acceleration(ee_acceleration)
        else:
            raise ValueError("Unrecognized goal type.")

        goal.error = error

    def is_done(self, goal: Goal) -> bool:
        """Returns True if the goal is reached."""
        if goal.error is None:
            return False

        error_norm = np.linalg.norm(goal.error)
        return bool(error_norm < 1e-3)


def run_controller(
    simulator: RobotSimulator,
    controller: RobotController,
    goal: Goal,
) -> None:
    # Run our controller, recording the joint state at each step.
    while not controller.is_done(goal):
        # Compute torque output and step.
        controller.update_control(goal)
        simulator.step()

    print(f"Goal error: {goal.error}")


def main(
    server: WebServer,
    simulator: RobotSimulator,
    pd_gains: PdGains,
) -> None:
    # Initialize controller.
    controller = RobotController(simulator, pd_gains=pd_gains)

    # 1. Position the end-effector above the box with joint space control.
    joint_position_goal = JointPositionGoal(
        np.array([-0.3, -0.8, -1.7, -1.7, -0.8, 1.8, -1.0])
    )

    print(f"\nMove to joint_position_goal: {joint_position_goal.goal}")
    run_controller(simulator, controller, joint_position_goal)

    # 2. Reach down and touch the box with operational space control.
    ee_position_goal = EePositionGoal(np.array([-0.45, -0.45, 0.1]))

    print(f"\nMove to ee_position_goal: {ee_position_goal.goal}")
    run_controller(simulator, controller, ee_position_goal)


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
    simulator.add_object("box", position=np.array([-0.45, -0.45, 0.05]))

    # Run main program when web page is loaded.
    server.on_ready(main, args=(server, simulator, pd_gains))
    server.connect(http_port=8000, ws_port=8001)
    server.wait()
