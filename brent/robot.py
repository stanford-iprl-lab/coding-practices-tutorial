"""(1/2) Variation/alternative to Toki's robot.py / simulator.py tutorial code.

This script should be runnable.

The main intentions of this version are:

1. Make it do something. Particularly for interactive debugging, seems nice if the code
   is actually intended to run and produce some result? In this case, we just run a PD
   controller on a fake (but somewhat realistic) simulator, and then plot the joint angles.

   > Not sure how important this actually is

2. Shortened significantly: I removed a lot of stuff which seemed nice for realism but
   not critical. (urdf, uid, properties, Pose class, IK, link IDs, etc)

3. Hyperfocused, I think too much, on type annotations as the takeaway, I think there
   were a lot of lessons on general code structure/logical flow in the original code, but
   kind of less clear to me how to present those parts?

See `robot_buggy.py` for how I'd imagine this would be presented.
"""


import argparse

import matplotlib.pyplot as plt
import numpy as np

from simulator import ScaraRobotSimulator


class ScaraRobotController:
    def __init__(self, simulator, joint_position_goal, pd_gains):
        self.simulator = simulator
        self.joint_position_goal = joint_position_goal
        self.pd_gains = pd_gains
        self.prev_error = 0.0

    def update_control(self):
        """Compute PD control output and pass it to the simulator."""
        error = self.joint_position_goal - self.simulator.get_joint_positions()
        error_delta = error - self.prev_error

        kp = self.pd_gains["kp"]
        kd = self.pd_gains["kd"]

        self.simulator.set_joint_torques(kp * error + kd * error_delta)
        self.prev_error = error

    def is_done(self):
        """Returns True if the goal is reached."""
        error_norm = np.linalg.norm(
            self.joint_position_goal - self.simulator.get_joint_positions()
        )
        return error_norm < 1e-5


def run_experiment_and_plot(simulator, controller):
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
    pd_gains = {
        "kp": args.kp,
        "kd": args.kd,
    }

    # Create our simulator and robot.
    simulator = ScaraRobotSimulator()
    controller = ScaraRobotController(
        simulator, joint_position_goal=[0.5, -0.2, 0.3], pd_gains=pd_gains
    )
    run_experiment_and_plot(simulator, controller)
