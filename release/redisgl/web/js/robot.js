/**
 * robot.js
 *
 * Copyright 2019. All Rights Reserved.
 *
 * Created: July 27, 2019
 * Authors: Toki Migimatsu
 */

import * as Graphics from "./graphics.js"
import * as Redis from "./redis.js"

var AXIS_WIDTH = 0.005;
var AXIS_SIZE = 0.1;

export function create(model, loadCallback) {
	const ab = model["articulated_body"];

	// Create base
	let base = new THREE.Object3D();
	const T_to_world = ab["T_base_to_world"];
	const quat = T_to_world["ori"];
	base.quaternion.set(quat["x"], quat["y"], quat["z"], quat["w"]);
	base.position.fromArray(T_to_world["pos"]);

	// Load base graphics
	let promises = [];
	ab.graphics.forEach((graphicsStruct) => {
		Graphics.parse(graphicsStruct, base, promises);
	});

	// Find end-effectors
	let ee_ids = new Set(Array.from(Array(ab.rigid_bodies.length).keys()));
	ab.rigid_bodies.forEach((rb) => {
		ee_ids.delete(rb.id_parent);
	});

	// Iterate over rigid bodies
	let bodies = [];
	ab["rigid_bodies"].forEach((rb) => {
		// Set parent
		let parent = rb["id_parent"] < 0 ? base : bodies[rb["id_parent"]];

		// Create body
		let body = new THREE.Object3D();
		const T_to_parent = rb["T_to_parent"];
		const quat = T_to_parent["ori"];
		body.quaternion.set(quat["x"], quat["y"], quat["z"], quat["w"]);
		body.position.fromArray(T_to_parent["pos"]);

		// Find joint axis
		let axis;
		switch (rb.joint.type[1].toLowerCase()) {
			case "x":
				axis = new THREE.Vector3(1, 0, 0);
				break;
			case "y":
				axis = new THREE.Vector3(0, 1, 0);
				break;
			case "z":
				axis = new THREE.Vector3(0, 0, 1);
				break;
		}

		// Add custom fields to THREE.Object3D
		body.redisgl = {
			quaternion: body.quaternion.clone(),
			position: body.position.clone(),
			jointType: rb.joint.type[0],
			jointAxis: axis
		};

		// Load body graphics
		rb.graphics.forEach((graphicsStruct) => {
			Graphics.parse(graphicsStruct, body, promises);
		});

		// Add frame axes
		let axes = Graphics.axes(AXIS_SIZE, AXIS_WIDTH);
		axes.visible = false;//rb.id_parent < 0 || ee_ids.has(rb.id);
		body.add(axes);

		// Add body to parent
		bodies.push(body);
		parent.add(body);
	});

	// Add custom field to THREE.Object3D
	base.redisgl = {
		bodies: bodies,
		q: bodies.map(() => 0)
	};

	Promise.all(promises).then(() => loadCallback(base));
	return base;
}

export function updateQ(robot, val) {
	const q = Redis.makeNumeric(val[0]);
	const spec = robot.redisgl;
	let bodies = spec.bodies;
	spec.q = q;

	for (var i = 0; i < bodies.length; i++) {
		let body = bodies[i];
		const spec = body.redisgl;

		// Update orientation in parent
		let quat = new THREE.Quaternion();
		if (spec.jointType.toLowerCase() == "r") {
			quat.setFromAxisAngle(spec.jointAxis, q[i]);
		}
		quat.premultiply(spec.quaternion);

		// Update position in parent
		let pos = new THREE.Vector3();
		if (spec.jointType.toLowerCase() == "p") {
			pos.copy(spec.jointAxis);
			pos.multiplyScalar(q[i]);
		}
		pos.add(spec.position);

		body.quaternion.copy(quat);
		body.position.copy(pos);
	}

	return true;
}

export function updatePosition(robot, val) {
	const pos = Redis.makeNumeric(val[0]);
	robot.position.fromArray(pos);
	return true;
}

export function updateOrientation(robot, val) {
	const quat = Redis.makeNumeric(val[0]);
	robot.quaternion.set(quat[0], quat[1], quat[2], quat[3]);
	return true;
}
