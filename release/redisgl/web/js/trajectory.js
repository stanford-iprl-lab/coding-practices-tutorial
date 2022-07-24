/**
 * trajectory.js
 *
 * Copyright 2019. All Rights Reserved.
 *
 * Created: July 27, 2019
 * Authors: Toki Migimatsu
 */

import * as Redis from "./redis.js"

var LEN_TRAJECTORY_TRAIL = 500;

export function create(model, loadCallback) {
	let traj = new THREE.Object3D();
	traj.redisgl = {
		idx: 0,
		len: 0,
	};

	let material = new THREE.LineBasicMaterial({ color: 0xffffff });
	let positions = new Float32Array(3 * (LEN_TRAJECTORY_TRAIL + 1));
	let buffer = new THREE.BufferAttribute(positions, 3);

	for (var i = 0; i < 2; i++) {
		let geometry = new THREE.BufferGeometry();
		geometry.setDrawRange(0, 0);
		geometry.setAttribute("position", buffer);
		traj.add(new THREE.Line(geometry, material));
	}

	loadCallback(traj);
	return traj;
}

export function appendPosition(traj, val) {
	const pos = Redis.makeNumeric(val[0]);
	let geometry1 = traj.children[0].geometry;
	let geometry2 = traj.children[1].geometry;
	let spec = traj.redisgl;

	geometry1.attributes.position.set(pos, 3 * spec.idx);
	spec.idx++;
	if (spec.idx > LEN_TRAJECTORY_TRAIL) {
		geometry1.attributes.position.set(pos, 0);
		spec.idx = 1;
	}

	if (spec.len < LEN_TRAJECTORY_TRAIL) {
		spec.len++;
		geometry1.setDrawRange(0, spec.len);
		geometry1.attributes.position.needsUpdate = true;
	} else {
		geometry1.setDrawRange(0, spec.idx);
		geometry1.attributes.position.needsUpdate = true;
		geometry2.setDrawRange(spec.idx, LEN_TRAJECTORY_TRAIL - spec.idx + 1);
		geometry2.attributes.position.needsUpdate = true;
	}
}

export function reset(traj) {
	let spec = traj.redisgl;
	spec.idx = 0;
	spec.len = 0;

	let geometry1 = traj.children[0].geometry;
	let geometry2 = traj.children[1].geometry;
	geometry1.setDrawRange(0, 0);
	geometry1.attributes.position.needsUpdate = true;
	geometry2.setDrawRange(0, 0);
	geometry2.attributes.position.needsUpdate = true;
}

