"""(2/2) This is a version of `robot.py`, with bugs that would be caught if we had type
annotations. Most of these are pretty obvious (typos, incorrect names) the only subtle
one is a bool vs np.bool_ comparison.


To make things interactive, perhaps the flow could be:

1. Introduction
2. Motivation

( Part 1: Type Annotations )

3. Interactive exercise time!
    - Introduce some fake scenario
        - we have some SCARA robot, a simulator (that we assume is fixed/working),
          trying to test a PD controller on it
        - Show the result of the working code
    - Show the code
        - One piece at a time via slides
        - Then, ask them to clone and give them some time to study it?
    - What does it do?
    - What do you like?
    - What would you change?
    - ^discuss these things
    - Without running it: can you find all the bugs?
    - Then: debug with the option of running
4. Why was debugging hard?
    - Python is a double-edged sword etc
    - Typing typing typing
5. What's the solution?
    - Type annotations in Python
6. VS Code Setup
    - Enable type checking etc?
7. Go through the buggy code, add annotations together
    - Annotate the input types: pretty much all the typos are caught
    - Convert the pd_gains dict to a dataclass: key error caught
    - Try running! It's still not working?
    - Annotate the output types: notice something funky with `is_goal_reached()`
8. Bonus:
    - Note on argparse, automating things like this


( Part 2: Functional Programming, More Exercises, etc )

...

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
        self.prev_error = None

    def update_control(self):
        """Compute PD control output and pass it to the simulator."""
        error = self.joint_position_goal - self.simulator.get_joint_position()
        error_delta = error - self.prev_error

        kp = self.pd_gains["Kp"]
        kd = self.pd_gains["Kd"]

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
    while controller.is_done() is False:
        # Compute torque output and step.
        controller.update_control()
        simulator.step()

        # Record state.
        joint_history.append(simulator.get_joint_position())

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
