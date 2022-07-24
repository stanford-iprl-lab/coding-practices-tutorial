#!/usr/bin/env python3

"""Interactive demo code: Part 2

This simulation contains a Franka Panda arm and a box. The arm starts off in its
home configuration, and it needs to reach over and touch the box in the corner.

We will use joint space control to safely position the arm above the box, and
then use Operational space control to bring the end-effector down to touch it.

This code is correctly annotated with types and passes static type checking, but
it still doesn't run correctly. Can you find the bugs?
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
            ee_acceleration = kp * error - kd * velocity

            self.simulator.set_ee_acceleration(ee_acceleration)

        self.error = error

    def is_done(self) -> bool:
        """Returns True if the goal is reached."""
        if self.error is None:
            return False

        error_norm = np.linalg.norm(self.error)
        return bool(error_norm < 1e-3)


def run_controller(simulator: RobotSimulator, controller: RobotController) -> None:
    """Runs the controller until it reaches the goal."""
    while not controller.is_done():
        # Compute torque output and step.
        controller.update_control()
        simulator.step()

    print(f"Goal error: {controller.error}")


def main(server: WebServer, simulator: RobotSimulator) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--kp", type=float, help="P gain.", default=49.0)
    parser.add_argument("--kd", type=float, help="D gain.", default=14.0)
    args = parser.parse_args()

    # Get control gains from argument parser.
    pd_gains = PdGains(kp=args.kp, kd=args.kd)

    # Initialize controller.
    controller = RobotController(simulator, pd_gains=pd_gains)

    # 1. Position the end-effector above the box with joint space control.
    joint_position_goal = np.array([-0.3, -0.8, -1.7, -1.7, -0.8, 1.8, -1.0])
    controller.set_goal(joint_position_goal=joint_position_goal)

    print(f"\nMove to joint_position_goal: {joint_position_goal}")
    run_controller(simulator, controller)

    # 2. Reach down and touch the box with operational space control.
    ee_position_goal = np.array([-0.45, -0.45, 0.1])
    controller.set_goal(ee_position_goal=ee_position_goal)

    print(f"\nMove to ee_position_goal: {ee_position_goal}")
    run_controller(simulator, controller)


if __name__ == "__main__":
    # Initialize the web server and simulator.
    server = WebServer()
    simulator = RobotSimulator(server)
    simulator.add_object("box", position=np.array([-0.45, -0.45, 0.05]))

    # Run main program when web page is loaded.
    server.on_ready(main, args=(server, simulator))
    server.connect(http_port=8000, ws_port=8001)
    server.wait()
