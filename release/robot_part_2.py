#!/usr/bin/env python3

"""Interactive demo code: Part 2

This simulation contains a Franka Panda arm and a box. The arm starts off in its
home configuration, and it needs to reach over and touch the box in the corner.

We will use joint space control to safely position the arm above the box, and
then use Operational space control to bring the end-effector down to touch it.

This code is correctly annotated with types and passes static type checking, but
it still doesn't run correctly. Can you find the bugs?
"""


from dataclasses import dataclass
from typing import Optional

import dcargs
import numpy as np
from simulator import RobotSimulator


@dataclass
class PdGains:
    kp: float
    """Proportional gain."""

    kd: float
    """Derivative gain."""


class RobotController:
    def __init__(self, simulator: RobotSimulator, pd_gains: PdGains):
        self.simulator = simulator
        self.pd_gains = pd_gains

        self.joint_position_goal: Optional[np.ndarray] = None
        self.ee_position_goal: Optional[np.ndarray] = None
        self.error: Optional[np.ndarray] = None

    def set_goal(
        self,
        joint_position_goal: Optional[np.ndarray] = None,
        ee_position_goal: Optional[np.ndarray] = None,
    ) -> None:
        """Sets a new joint position or end-effector position goal."""
        if joint_position_goal is not None:
            self.joint_position_goal = joint_position_goal
        elif ee_position_goal is not None:
            self.ee_position_goal = ee_position_goal

    def run(self):
        """Runs the controller until it reaches the goal."""
        while self.is_done() is False:
            # Compute torque output and step.
            self.update_control()
            self.simulator.step()

        assert self.error is not None
        print()
        print(f"Time elapsed: {simulator.get_simulation_time()} seconds.")
        print(f"Final error:  {np.linalg.norm(self.error)}")

    def update_control(self) -> None:
        """Compute PD control output and pass it to the simulator."""
        kp = self.pd_gains.kp
        kd = self.pd_gains.kd

        if self.joint_position_goal is not None:
            error = self.joint_position_goal - self.simulator.get_joint_positions()
            velocity = self.simulator.get_joint_velocities()
            joint_accelerations = kp * error - kd * velocity

            self.simulator.set_joint_accelerations(joint_accelerations)
            self.error = error

        elif self.ee_position_goal is not None:
            error = self.ee_position_goal - self.simulator.get_ee_position()
            velocity = self.simulator.get_ee_velocity()
            ee_acceleration = kp * error - kd * velocity

            self.simulator.set_ee_acceleration(ee_acceleration)
            self.error = error

    def is_done(self) -> bool:
        """Returns True if the goal is reached."""
        if self.error is None:
            return False

        error_norm = np.linalg.norm(self.error)
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
    joint_position_goal = np.array([-0.3, -0.8, -1.7, -1.7, -0.8, 1.8, -1.0])
    controller.set_goal(joint_position_goal=joint_position_goal)
    print(f"\nMove to joint_position_goal: {joint_position_goal}")
    controller.run()

    # 2. Reach down and touch the box with operational space control.
    ee_position_goal = np.array([-0.45, -0.45, 0.1])
    controller.set_goal(ee_position_goal=ee_position_goal)
    print(f"\nMove to ee_position_goal: {ee_position_goal}")
    controller.run()
