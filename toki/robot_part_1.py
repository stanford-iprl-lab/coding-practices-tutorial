#!/usr/bin/env python3

"""Interactive demo code: Part 1

This simulation contains a Franka Panda arm. We want to move the arm from its
home configuration to a new joint configuration.

This code contains several minor bugs. Can you spot them?
"""

import argparse
from dataclasses import dataclass

import numpy as np

from simulator import RobotSimulator
from redisgl.server import WebServer


class RobotController:
    def __init__(self, simulator, pd_gains, joint_position_goal):
        self.simulator = simulator
        self.pd_gains = pd_gains
        self.joint_position_goal = joint_position_goal
        self.error = None

    def update_control(self):
        """Compute PD control output and pass it to the simulator."""
        kp = self.pd_gains["kp"]
        kd = self.pd_gains["kd"]

        error = self.joint_position_goal - self.simulator.get_joint_positions()
        velocity = self.simulator.get_joint_velocities()
        joint_accelerations = kp * error - kd * velocity

        self.simulator.set_joint_accelerations(joint_accelerations)
        self.error = error

    def is_done(self):
        """Returns True if the goal is reached."""
        if self.error is None:
            return False

        error_norm = np.linalg.norm(self.error)
        return error_norm < 1e-3


def run_controller(simulator, controller):
    """Runs the controller until it reaches the goal."""
    while not controller.is_done():
        # Compute torque output and step.
        controller.update_control()
        simulator.step()

    print(f"Goal error: {controller.error}")


def main(server, simulator):
    parser = argparse.ArgumentParser()
    parser.add_argument("--kp", type=float, help="P gain.", default=49.0)
    parser.add_argument("--kd", type=float, help="D gain.", default=14.0)
    args = parser.parse_args()

    # Get control gains from argument parser.
    pd_gains = {
        "kp": args.kp,
        "kd": args.kd,
    }

    # Initialize controller.
    joint_position_goal = np.array([-0.3, -0.8, -1.7, -1.7, -0.8, 1.8, -1.0])
    controller = RobotController(
        simulator, joint_position_goal=joint_position_goal, pd_gains=pd_gains
    )

    # Run controller.
    print(f"\nMove to joint_position_goal: {joint_position_goal}")
    run_controller(simulator, controller)


if __name__ == "__main__":
    # Initialize the web server and simulator.
    server = WebServer()
    simulator = RobotSimulator(server)

    # Run main program when web page is loaded.
    server.on_ready(main, args=(server, simulator))
    server.connect(http_port=8000, ws_port=8001)
    server.wait()
