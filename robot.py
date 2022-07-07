import numpy as np

from simulator import Simulator
from pose import Pose


class JointConfigurationGoal:
    def __init__(self):
        self.reset()

    # (1) The boilerplate for these properties could be handled by dataclass.
    # TODO: Make JointConfigurationGoal a dataclass.
    @property
    def q(self):
        return self._q

    @property
    def threshold(self):
        return self._threshold

    @property
    def start_time(self):
        return self._start_time

    @property
    def timeout(self):
        return self._timeout

    def reset(self):
        # (3) There's a lot of overhead here in trying to specify a "null"
        # JointConfigurationGoal. This also allows more room for potential bugs
        # if we want to add more fields to this class but forget to handle them
        # in self.reset() or self.set(). Or if we attempt to perform
        # computations with a null goal.
        # TODO: Use Optional[JointConfigurationGoal] to specify a null goal.
        # Type checking will ensure we don't perform computations with null
        # values.
        self._q = None
        self._start_time = None
        self._timeout = None
        self._threshold = None

    def set(self, q, start_time, timeout, threshold):
        self._q = q
        self._start_time = start_time
        self._timeout = timeout
        self._threshold = threshold

    def is_set(self):
        return self.q is not None

    def is_timed_out(self, time):
        # (2) There's a bug here where self.start_time + self.timeout can't be
        # computed if either one is None. This bug could easily be detected with
        # type hints.
        # TODO: Add type hints.
        return time > self.start_time + self.timeout

    def is_converged(self, q_current):
        q_err = q_current - self.q
        return (np.abs(q_err) < self.threshold).all()


class PoseGoal(JointConfigurationGoal):
    @property
    def link_id(self):
        return self._link_id

    @property
    def pose(self):
        return self._pose

    def reset(self):
        self._link_id = None
        self._pose = None
        super().reset()

    def set(
        self,
        link_id,
        pose,
        start_time,
        timeout,
        threshold,
    ):
        self._link_id = link_id
        self._pose = pose
        self._start_time = start_time
        self._timeout = timeout
        self._threshold = threshold

    def is_set(self):
        # (3) We have to override JointConfigurationGoal.is_set() here because
        # it checks if self.q is None, but we don't set self.q in self.set().
        # This could be easy to overlook if we create a new subclass of
        # JointConfigurationGoal.
        return self.pose is not None


class Robot:
    def __init__(self, simulator, urdf):
        self._simulator = simulator
        self._uid = self.simulator.add_body(urdf)

        # (4) This class was written with separate member variables for
        # joint configuration and pose goals. A robot can only handle one goal
        # at a time, so keeping both variables requires us to remember to deal
        # with both in all our member functions.
        # TODO: Replace with a Union[JointConfigurationGoal, PoseGoal], let type
        # checking remind us to handle both types.
        self._q_goal = JointConfigurationGoal()
        self._pose_goal = PoseGoal()

    @property
    def simulator(self):
        return self._simulator

    @property
    def uid(self):
        return self._uid

    def joint_configuration(self):
        return self.simulator.joint_positions(self.uid)

    def set_joint_configuration_goal(self, q, timeout=15.0, threshold=0.001):
        self._q_goal.set(
            q,
            start_time=self.simulator.time(),
            timeout=timeout,
            threshold=threshold,
        )

    def set_pose_goal(self, pose, link_id=-1, timeout=15.0, threshold=0.001):
        self._pose_goal.set(
            link_id=link_id,
            pose=pose,
            start_time=self.simulator.time(),
            timeout=timeout,
            threshold=threshold,
        )

    def update_control(self):
        # (4) The control flow of this function is hard to parse. The first
        # problem is that self._pose_goal and self._q_goal are being modified
        # almost at every line, so we need to read every line carefully and
        # build a mental picture of the possible states of self._pose_goal and
        # self._q_goal to understand this function.
        # TODO: Refactor to minimize modifications of self._pose_goal and
        # self._q_goal.
        if self._pose_goal.is_set():
            if self._pose_goal.is_timed_out(self.simulator.time()):
                self._pose_goal.reset()
                self._q_goal.reset()
                return

            if not self._q_goal.is_set():
                # (4) self._update_ik modifies self._q_goal, but this isn't
                # clear at all from the function signature.
                # TODO: Make self._update_ik a pure function. Or just compute ik
                # at self.set_pose_goal() and remove it altogether.
                self._update_ik()

        # (4) The choice of if instead of elif here is crucial, but it's not
        # obvious unless we understand what's happening above.
        if self._q_goal.is_set():
            if self._q_goal.is_timed_out(
                self.simulator.time()
            ) or self._q_goal.is_converged(self.joint_configuration()):
                self._pose_goal.reset()
                self._q_goal.reset()
                return

            self.simulator.position_control(
                self.uid,
                target_positions=self._q_goal.q,
            )

    def _update_ik(self):
        self._q_goal.set(
            self.simulator.compute_inverse_kinematics(
                self._pose_goal.link_id,
                self._pose_goal.pose,
            ),
            start_time=self._pose_goal.start_time,
            timeout=self._pose_goal.timeout,
            threshold=self._pose_goal.threshold,
        )

    def is_done(self):
        return not self._pose_goal.is_set() and not self._q_goal.is_set()


if __name__ == "__main__":
    simulator = Simulator()
    robot = Robot(simulator, "franka_panda.urdf")

    pose = Pose(position=np.array([0.4, 0.0, 0.4]))
    robot.set_pose_goal(pose)
    while not robot.is_done():
        robot.update_control()
        simulator.step()
