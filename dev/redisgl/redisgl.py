import abc
import dataclasses
import json
from typing import Any, Dict, Optional, Sequence, Tuple, Union

import numpy as np


@dataclasses.dataclass
class Pose:
    """6d pose.

    Args:
        pos: 3d position.
        quat: xyzw quaternion.
    """

    pos: np.ndarray = np.zeros(3)
    quat: np.ndarray = np.array([0.0, 0.0, 0.0, 1.0])

    def to_dict(self) -> Dict[str, Any]:
        """Converts a pose to dict format."""
        return {
            "pos": self.pos.tolist(),
            "ori": {
                "x": self.quat[0],
                "y": self.quat[1],
                "z": self.quat[2],
                "w": self.quat[3],
            },
        }


class Geometry(abc.ABC):
    @abc.abstractmethod
    def to_dict(self) -> Dict[str, Any]:
        pass


class Box(Geometry):
    type = "box"

    def __init__(self, scale: Union[Sequence[float], np.ndarray]):
        self.scale = list(scale)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type,
            "scale": self.scale,
        }


class Capsule(Geometry):
    type = "capsule"

    def __init__(self, radius: float, length: float):
        self.radius = radius
        self.length = length

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type,
            "radius": self.radius,
            "length": self.length,
        }


class Cylinder(Geometry):
    type = "cylinder"

    def __init__(self, radius: float, length: float):
        self.radius = radius
        self.length = length

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type,
            "radius": self.radius,
            "length": self.length,
        }


class Sphere(Geometry):
    type = "sphere"

    def __init__(self, radius: float):
        self.radius = radius

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type,
            "radius": self.radius,
        }


class Mesh(Geometry):
    type = "mesh"

    def __init__(self, path: str, scale: Union[Sequence[float], np.ndarray]):
        self.path = path
        self.scale = list(scale)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type,
            "mesh": self.path,
            "scale": self.scale,
        }


@dataclasses.dataclass
class Material:
    name: str = ""
    rgba: Tuple[float, float, float, float] = (1.0, 1.0, 1.0, 1.0)
    texture: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "rgba": self.rgba,
            "texture": self.texture,
        }


@dataclasses.dataclass
class Graphics:
    name: str
    geometry: Geometry
    material: Material = Material()
    T_to_parent: Pose = Pose()

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "T_to_parent": self.T_to_parent.to_dict(),
            "geometry": self.geometry.to_dict(),
            "material": self.material.to_dict(),
        }


@dataclasses.dataclass
class ModelKeys:
    key_namespace: str
    key_robots_prefix: str
    key_objects_prefix: str
    key_trajectories_prefix: str
    key_cameras_prefix: str

    def __init__(self, key_namespace: str):
        self.key_namespace = key_namespace
        self.key_robots_prefix = f"{key_namespace}::model::robot::"
        self.key_objects_prefix = f"{key_namespace}::model::object::"
        self.key_trajectories_prefix = f"{key_namespace}::model::trajectory::"
        self.key_cameras_prefix = f"{key_namespace}::model::camera::"


def register_object(
    redis,
    model_keys: ModelKeys,
    name: str,
    graphics: Union[Graphics, Sequence[Graphics]],
    key_pos: str,
    key_ori: str = "",
    key_scale: str = "",
    key_matrix: str = "",
    axis_size: float = 0.01,
) -> None:
    """Registers an object with Redis.

    Args:
        redis: Redis client.
        model_keys: Model keys.
        name: Redis object name.
        graphics: Graphics object or list of graphics.
        key_pos: Position Redis key.
        key_ori: Optional orientation Redis key.
        key_scale: Optioanl scale redis key.
        key_matrix: Optional matrix transformation Redis key.
        axis_size: Size of visualization for object xyz axes.
    """

    if isinstance(graphics, Graphics):
        graphics = [graphics]

    redis.set(
        model_keys.key_objects_prefix + name,
        json.dumps(
            {
                "graphics": [g.to_dict() for g in graphics],
                "key_pos": key_pos,
                "key_ori": key_ori,
                "key_scale": key_scale,
                "key_matrix": key_matrix,
                "axis_size": axis_size,
            }
        ),
    )


def register_robot(
    redis, model_keys: ModelKeys, ab, key_q: str, key_pos: str = "", key_ori: str = ""
) -> None:
    redis.set(
        model_keys.key_robots_prefix + ab.name,
        json.dumps(
            {
                "articulated_body": "%ARTICULATED_BODY",
                "key_q": key_q,
                "key_pos": key_pos,
                "key_ori": key_ori,
            }
        )
        .replace("\\", "")
        .replace('"%ARTICULATED_BODY"', str(ab)),
    )


def register_trajectory(redis, model_keys: ModelKeys, name: str, key_pos: str) -> None:
    redis.set(
        model_keys.key_trajectories_prefix + name, json.dumps({"key_pos": key_pos})
    )


def register_model_keys(redis, model_keys: ModelKeys) -> None:
    redis.set(
        f"webapp::simulator::args::{model_keys.key_namespace}",
        json.dumps(
            {
                "key_robots_prefix": model_keys.key_robots_prefix,
                "key_objects_prefix": model_keys.key_objects_prefix,
                "key_trajectories_prefix": model_keys.key_trajectories_prefix,
                "key_cameras_prefix": model_keys.key_cameras_prefix,
            }
        ),
    )
