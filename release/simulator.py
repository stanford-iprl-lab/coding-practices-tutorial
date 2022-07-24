"""Simple physics simulator for a 3 degree-of-freedom SCARA robot.

For the sake of this tutorial, we'll consider this as fixed, and focus on how we can
improve `robot.py`!"""

import threading
import time

import ctrlutils
import numpy as np
import numpy.typing as npt
import spatialdyn as dyn
from ctrlutils import eigen
from redisgl import redisgl
from redisgl.server import WebServer


class RobotSimulator:
    TIMESTEP = 1 / 1000
    URDF = "redisgl/web/resources/franka_panda.urdf"
    Q_HOME = np.array([0, -np.pi / 6, 0, -5 * np.pi / 6, 0, 2 * np.pi / 3, np.pi / 4])
    QUAT_HOME = eigen.Quaterniond(w=0, x=1, y=0, z=0) * eigen.Quaterniond(
        eigen.AngleAxisd(np.pi / 4, np.array([0.0, 0.0, 1.0]))
    )
    EE_OFFSET = np.array([0.0, 0.0, 0.214])

    def __init__(self):
        self.redis = WebServer()

        self.ab = dyn.urdf.load_model(self.URDF)
        self.ab.q = self.Q_HOME

        self.command_tau = np.zeros_like(self.ab.q)
        self.num_iters = 0

        # Setup robot in Redis.
        # redis.sadd("webapp::resources::simulator", str(path_resources))
        self.model_keys = redisgl.ModelKeys("simulator")
        redisgl.register_model_keys(self.redis, self.model_keys)
        redisgl.register_robot(
            self.redis, self.model_keys, self.ab, "franka_panda::joint_positions"
        )
        redisgl.register_trajectory(
            self.redis, self.model_keys, "x_ee", "franka_panda::ee_position"
        )
        self._update_redis(commit=False)

    def wait_until_web_browser_connected(self) -> None:
        """Wait until a web browser has opened the visualizer."""
        self.redis.on_ready(lambda *unused: None)
        self.redis.connect(http_port=8000, ws_port=8001, verbose=False)
        self.redis.wait()

    def get_simulation_time(self) -> float:
        """Get the current simulation time, in seconds."""
        return self.num_iters * self.TIMESTEP

    def get_joint_positions(self) -> npt.NDArray[np.float64]:
        """Get joint positions for our robot."""
        return self.ab.q

    def get_joint_velocities(self) -> npt.NDArray[np.float64]:
        """Get joint velocities for our robot."""
        return self.ab.dq

    def get_ee_position(self) -> npt.NDArray[np.float64]:
        """Get the end-effector position for our robot."""
        return dyn.cartesian_pose(self.ab, offset=self.EE_OFFSET).translation

    def get_ee_velocity(self) -> npt.NDArray[np.float64]:
        """Get the end-effector velocity for our robot."""
        return dyn.jacobian(self.ab, offset=self.EE_OFFSET)[:3] @ self.ab.dq

    def set_joint_accelerations(self, ddq: npt.NDArray[np.float64]) -> None:
        """Set the command joint acceleration."""
        self.command_tau = dyn.inverse_dynamics(self.ab, ddq)

    def set_ee_acceleration(self, ddx: npt.NDArray[np.float64]) -> None:
        """Set the command end-effector acceleration."""
        KP_ORI, KV_ORI = 100, 20
        KP_JOINT, KV_JOINT = 5, 20

        # Decide whether orientation is controllable.
        J = dyn.jacobian(self.ab, offset=self.EE_OFFSET)
        if dyn.opspace.is_singular(self.ab, J, svd_epsilon=0.01):
            # Give up on orientation.
            J = J[:3]
        else:
            # Compute orientation control.
            quat = eigen.Quaterniond(dyn.cartesian_pose(self.ab).linear)
            quat_des = ctrlutils.near_quaternion(self.QUAT_HOME, quat)
            w = J[3:] @ self.ab.dq
            dw = -KP_ORI * ctrlutils.orientation_error(quat, quat_des) - KV_ORI * w
            ddx = np.concatenate((ddx, dw))

        # Compute opspace torques.
        N = np.eye(self.ab.dof)
        self.command_tau = dyn.opspace.inverse_dynamics(self.ab, J, ddx, N)

        # Compute nullspace torques.
        ddq = -KP_JOINT * (self.ab.q - self.Q_HOME) - KV_JOINT * self.ab.dq
        self.command_tau += dyn.opspace.inverse_dynamics(
            self.ab, np.eye(self.ab.dof), ddq, N
        )

        # Compensate gravity.
        self.command_tau += dyn.gravity(self.ab)

    def step(self) -> None:
        """Take one physics simulation step."""
        dyn.integrate(self.ab, self.command_tau, self.TIMESTEP)
        self._update_redis()
        self.num_iters += 1
        time.sleep(self.TIMESTEP)

    def add_object(self, name: str, position: npt.NDArray[np.float64]) -> None:
        graphics = redisgl.Graphics(name, redisgl.Box(np.array([0.1, 0.1, 0.1])))
        redisgl.register_object(
            self.redis,
            self.model_keys,
            name,
            graphics,
            key_pos=f"{name}::position",
        )
        self.redis.set_matrix(f"{name}::position", position)

    def _update_redis(self, commit: bool = True) -> None:
        self.redis.set_matrix(
            "franka_panda::joint_positions", self.get_joint_positions()
        )
        self.redis.set_matrix(
            "franka_panda::joint_velocities", self.get_joint_velocities()
        )
        self.redis.set_matrix("franka_panda::ee_position", self.get_ee_position())
        self.redis.set_matrix("franka_panda::ee_velocity", self.get_ee_velocity())
        if commit:
            self.redis.commit()
