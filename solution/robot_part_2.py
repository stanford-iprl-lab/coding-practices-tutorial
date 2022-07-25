#!/usr/bin/env python3

"""Interactive demo code: Part 2

This simulation contains a Franka Panda arm and a box. The arm starts off in its
home configuration, and it needs to reach over and touch the box in the corner.

We will use joint space control to safely position the arm above the box, and
then use Operational space control to bring the end-effector down to touch it.

This code is correctly annotated with types and passes static type checking, but
it still doesn't run correctly. Can you find the bugs?
"""


"""Solution notes --

(1) Typing

    The current implementation has two member variables,
    `self.joint_position_goal` and `self.ee_position_goal`, although only one
    can be set at a time. This results in error-prone if/else checks to see
    which goal is set.

    Solution:

    Let typing enforce this logic. We can can remove the need for individual
    checks with one `self.goal: Union[JointPositionGoal, EePositionGoal]`
    variable.

(2) Pure functions

    If `self.error` doesn't get reset properly when `self.set_goal()` is called,
    then there could be some strange behavior leftover from the previous goal.

    Solution:

    Side effects like this can be tricky to catch/keep track of. One extreme is
    to make functions as pure as possible, e.g., having the user hold the
    mutable state.
"""
from dataclasses import dataclass
from typing import Optional, Union

import dcargs
import numpy as np
from simulator import RobotSimulator


@dataclass
class PdGains:
    kp: float
    """Proportional gain."""

    kd: float
    """Derivative gain."""


@dataclass
class JointPositionGoal:
    goal: np.ndarray


@dataclass
class EePositionGoal:
    goal: np.ndarray


class RobotController:
    def __init__(self, simulator: RobotSimulator, pd_gains: PdGains):
        self.simulator = simulator
        self.pd_gains = pd_gains

        self.goal: Optional[Union[JointPositionGoal, EePositionGoal]] = None

    def set_goal(self, goal: Union[JointPositionGoal, EePositionGoal]) -> None:
        """Sets a new joint position or end-effector position goal."""
        self.goal = goal

    def run(self):
        """Runs the controller until it reaches the goal."""
        error = None
        while not self.is_done(error):
            # Compute torque output and step.
            error = self.update_control()
            self.simulator.step()

        print()
        print(f"Time elapsed: {simulator.get_simulation_time()} seconds.")
        print(f"Final error:  {error}")

    def update_control(self) -> float:
        """Compute PD control output and pass it to the simulator. Returns the error."""
        kp = self.pd_gains.kp
        kd = self.pd_gains.kd

        if isinstance(self.goal, JointPositionGoal):
            error = self.goal.goal - self.simulator.get_joint_positions()
            velocity = self.simulator.get_joint_velocities()
            joint_accelerations = kp * error - kd * velocity

            self.simulator.set_joint_accelerations(joint_accelerations)

        elif isinstance(self.goal, EePositionGoal):
            error = self.goal.goal - self.simulator.get_ee_position()
            velocity = self.simulator.get_ee_velocity()
            ee_acceleration = kp * error - kd * velocity

            self.simulator.set_ee_acceleration(ee_acceleration)

        else:
            raise ValueError("Unrecognized goal type.")

        return float(np.linalg.norm(error))

    def is_done(self, error: Optional[np.ndarray]) -> bool:
        """Returns True if the goal is reached."""
        if error is None:
            return False

        error_norm = np.linalg.norm(error)
        return bool(error_norm < 1e-3)


if __name__ == "__main__":
    # Parse arguments. Reasonable initial values: kp=49, kd=14.0.
    pd_gains = dcargs.cli(PdGains)

    # Initialize the web server and simulator.
    simulator = RobotSimulator()
    simulator.add_object("box", position=np.array([-0.45, -0.45, 0.05]))
    simulator.wait_until_web_browser_connected()

    # Initialize controller.
    controller = RobotController(simulator, pd_gains=pd_gains)

    # 1. Position the end-effector above the box with joint space control.
    joint_position_goal = JointPositionGoal(
        np.array([-0.3, -0.8, -1.7, -1.7, -0.8, 1.8, -1.0])
    )
    controller.set_goal(joint_position_goal)
    print(f"\nMove to joint_position_goal: {joint_position_goal.goal}")
    controller.run()

    # 2. Reach down and touch the box with operational space control.
    ee_position_goal = EePositionGoal(np.array([-0.45, -0.45, 0.1]))
    controller.set_goal(ee_position_goal)
    print(f"\nMove to ee_position_goal: {ee_position_goal.goal}")
    controller.run()
