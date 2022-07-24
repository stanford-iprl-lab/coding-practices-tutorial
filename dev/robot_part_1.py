#!/usr/bin/env python3

"""Interactive demo code: Part 1

This simulation contains a Franka Panda arm. We want to move the arm from its
home configuration to a new joint configuration.

This code contains several minor bugs. Can you spot them?
"""

import argparse
import time
from dataclasses import dataclass

import numpy as np
from simulator import RobotSimulator

SOLUTION = True


class RobotController:
    def __init__(self, simulator, pd_gains, joint_position_goal):
        self.simulator = simulator
        self.pd_gains = pd_gains
        self.joint_position_goal = joint_position_goal
        self.error = None

    def run(self):
        """Runs the controller until it reaches the goal."""
        if SOLUTION:
            while not self.is_done():
                # Compute torque output and step.
                self.update_control()
                self.simulator.step()
        else:
            while self.is_done() is False:
                # Compute torque output and step.
                self.update_control()
                self.simulator.step()

        assert self.error is not None
        print()
        print(f"Time elapsed: {simulator.get_simulation_time()} seconds.")
        print(f"Final error:  {np.linalg.norm(self.error)}")

    def update_control(self):
        """Compute PD control output and pass it to the simulator."""
        if SOLUTION:
            kp = self.pd_gains["kp"]
            kd = self.pd_gains["kd"]
        else:
            kp = self.pd_gains["Kp"]
            kd = self.pd_gains["Kd"]

        if SOLUTION:
            error = self.joint_position_goal - self.simulator.get_joint_positions()
            velocity = self.simulator.get_joint_velocities()
            joint_acceleration = kp * error - kd * velocity
            self.simulator.set_joint_accelerations(joint_acceleration)
        else:
            error = self.joint_position_goal - self.simulator.get_joint_position()
            velocity = self.simulator.get_joint_velocity()
            joint_acceleration = kp * error - kd * velocity
            self.simulator.set_joint_acceleration(joint_acceleration)
        self.error = error

    def is_done(self):
        """Returns True if the goal is reached."""
        if self.error is None:
            return False
        error_norm = np.linalg.norm(self.error)
        return error_norm < 1e-3


if __name__ == "__main__":
    # Parse arguments. Reasonable initial values: kp=49, kd=14.0.
    parser = argparse.ArgumentParser()
    parser.add_argument("--kp", type=float, help="P gain.", required=True)
    parser.add_argument("--kd", type=float, help="D gain.", required=True)
    args = parser.parse_args()

    # Initialize the web server and simulator.
    simulator = RobotSimulator()
    simulator.wait_until_web_browser_connected()

    # Initialize controller.
    joint_position_goal = np.array([-0.3, -0.8, -1.7, -1.7, -0.8, 1.8, -1.0])
    controller = RobotController(
        simulator,
        joint_position_goal=joint_position_goal,
        pd_gains={"kp": args.kp, "kd": args.kd},
    )

    # Run controller.
    print(f"Move to {joint_position_goal=}")
    controller.run()
