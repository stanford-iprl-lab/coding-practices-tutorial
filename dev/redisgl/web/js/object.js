/**
 * object.js
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
	// Create object
	let object = new THREE.Object3D();

	// Load graphics
	let promises = [];
	model["graphics"].forEach((graphicsStruct) => {
		Graphics.parse(graphicsStruct, object, promises);
	});
	const axis_size = "axis_size" in model ? model["axis_size"] : AXIS_SIZE;
	object.add(Graphics.axes(axis_size, AXIS_WIDTH));


	Promise.all(promises).then(() => loadCallback(object));
	return object;
}

export function updatePosition(object, val) {
	const pos = Redis.makeNumeric(val[0]);
	if (object.matrixAutoUpdate) {
		object.position.fromArray(pos);
	} else {
		object.matrix.setPosition(pos[0], pos[1], pos[2]);
	}
	return true;
}

export function updateOrientation(object, val) {
	const quat = Redis.makeNumeric(val[0]);
	object.quaternion.set(quat[0], quat[1], quat[2], quat[3]);
	return true;
}

export function updateScale(object, val) {
	const scale = Redis.makeNumeric(val[0]);
	object.scale.fromArray(scale);
	return true;
}

export function updateMatrix(object, val) {
	const arr = [].concat.apply([], Redis.makeNumeric(val));  // Flatten matrix.
	if (arr.length == 9) {
		const position = object.matrixAutoUpdate
			? object.position
			: new THREE.Vector3().setFromMatrixPosition(object.matrix);

		const matrix = new THREE.Matrix3().fromArray(arr);
		object.matrix.setFromMatrix3(matrix);
		object.matrix.setPosition(position);
	} else if (arr.length == 16) {
		object.matrix.fromArray(arr);
	} else {
		console.error("Invalid matrix size: " + matrix.length);
	}
	object.matrixAutoUpdate = false;
	return true;
}

