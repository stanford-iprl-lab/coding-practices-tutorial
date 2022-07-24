/**
 * simulator.js
 *
 * Author: Toki Migimatsu
 * Created: December 2017
 */

import * as Camera from "./camera.js"
import * as Graphics from "./graphics.js"
import * as GraphicsObject from "./object.js"
import * as Redis from "./redis.js"
import * as Robot from "./robot.js"
import * as Trajectory from "./trajectory.js"

var AXIS_WIDTH = 0.005;
var AXIS_SIZE = 0.1;

var KEY_ARGS = "webapp::simulator::args";
var KEY_INTERACTION = "webapp::simulator::interaction";
var KEY_CAMERA_POS = "webapp::simulator::camera::pos";
var KEY_CAMERA_TARGET = "webapp::simulator::camera::target";
var KEY_TRAJ_RESET = "webapp::simulator::trajectory::reset";
var KEY_AXES_VISIBLE = "webapp::simulator::axes::visible";

$(document).ready(function() {

	let handlingMessage = false;

	function setupWebSocket() {
		$.get("/get_websocket_port", function(ws_port) {
			const ws_url = "ws://" + window.location.hostname + ":" + ws_port
			let ws = new WebSocket(ws_url);
			console.log("WebSocket connection established at " + ws_url);

			ws.onmessage = (e) => {
				if (handlingMessage) return;
				handlingMessage = true;
				new Response(e.data).arrayBuffer().then(handleMessage);
			};
			ws.onclose = (_) => {
				setupWebSocket();
			};
		}).fail(function() {
			setTimeout(setupWebSocket, 1000);
		});
	}
	setupWebSocket();

	let camera, scene, renderer, raycaster, controls;

	let interaction = {
		key_object: "",
		idx_link: 0,
		pos_click_in_link: [0, 0, 0],
		pos_mouse_in_world: [0, 0, 0],
		modifier_keys: [],
		key_down: ""
	};
	let lineMouseDrag = null;

	let redisUpdateCallbacks = {};
	let args = {};
	let robots = {};
	let objects = {};
	let trajectories = {};
	let cameras = {};

	initGraphics();

	function handleMessage(buffer) {
		const keys = Redis.parseMessage(buffer);

		// Initialize webapp args
		parseArgs(keys.toUpdate);

		// Parse models
		parseModels(keys.toUpdate);

		// Parse remaining update keys
		let renderFrame = parseUpdateKeys(keys.toUpdate);

		// Parse delete keys
		renderFrame = parseDeleteKeys(keys.toDelete) || renderFrame;

		// Render
		if (renderFrame) {
			renderer.render(scene, camera);
		}
		handlingMessage = false;
	};

	function registerRedisUpdateCallback(key, keyComponent, component, updateCallback) {
		if (key === "") return;
		if (!(key in redisUpdateCallbacks)) {
			redisUpdateCallbacks[key] = [];
		}
		let renderCallback = (callback) => {
			renderer.render(scene, camera);
			if (callback) callback();
		};
		redisUpdateCallbacks[key][keyComponent] = (val) => {
			return updateCallback(component, val, renderCallback);
		};
		// Run callback immediately if key already exists
		if (Redis.formExists(key)) {
			updateCallback(component, Redis.getValue(key), renderCallback);
		}
	}

	function unregisterRedisUpdateCallback(keyComponent) {
		for (const key in redisUpdateCallbacks) {
			if (!(keyComponent in redisUpdateCallbacks[key])) continue;
			delete redisUpdateCallbacks[key][keyComponent];
		}
	}

	function parseArgs(keyVals) {
		for (const key in keyVals) {
			const regex = new RegExp("^" + KEY_ARGS + "::(.*)$");
			const matches = regex.exec(key);
			if (matches === null) continue;
			const namespace = matches[1];

			try {
				args[namespace] = JSON.parse(keyVals[key]);
			} catch (error) {
				console.error(error);
				console.error("Failed to parse args " + key + ":\n" + keyVals[key]);
				continue;
			}

			console.log("New args: " + key);

			// Load already existing models
			Redis.getKeys().forEach((key) => {
				let parseModelFunction;
				if (key.startsWith(args[namespace]["key_cameras_prefix"])) {
					parseModelFunction = parseCameraModel;
				} else if (key.startsWith(args[namespace]["key_objects_prefix"])) {
					parseModelFunction = parseObjectModel;
				} else if (key.startsWith(args[namespace]["key_robots_prefix"])) {
					parseModelFunction = parseRobotModel;
				} else if (key.startsWith(args[namespace]["key_trajectories_prefix"])) {
					parseModelFunction = parseTrajectoryModel;
				} else {
					return;
				}
				const val = Redis.getValue(key);
				parseModelFunction(key, val);
			});
		}
	}

	function parseModels(keyVals) {
		for (const key in keyVals) {
			let val = keyVals[key];

			// Skip binary objects
			if (typeof (val) === "object") continue;

			// Try parsing all model types
			try {
				if (!parseCameraModel(key, val) &&
					!parseObjectModel(key, val) &&
					!parseRobotModel(key, val) &&
					!parseTrajectoryModel(key, val)) continue;
			} catch (error) {
				console.error(error);
				console.error("Failed to parse model " + key + ":\n" + val);
				return false;
			}

			// Update html
			Redis.updateForm(key, val, true, true, true);
		}
	}

	function isModelKey(key, keyPrefix) {
		for (const modelKeys in args) {
			if (args[modelKeys][keyPrefix] !== "" &&
				key.startsWith(args[modelKeys][keyPrefix])) return true;
		}
		return false;
	}

	function parseRobotModel(key, val) {
		if (!isModelKey(key, "key_robots_prefix")) return false;

		// Parse robot model
		const model = JSON.parse(val);
		addComponentToScene(Robot, robots, key, model, (_) => {
			$.ajax({
				method: "POST",
				url: "/READY",
				data: {"robot": ""},
			});
		});
		registerRedisUpdateCallback(model["key_q"], key, robots[key], (robot, val) => {
			const renderFrame = Robot.updateQ(robot, val);
			updateInteraction(key, robot.redisgl.bodies);
			return renderFrame;
		});
		registerRedisUpdateCallback(model["key_pos"], key, robots[key], Robot.updatePosition);
		registerRedisUpdateCallback(model["key_ori"], key, robots[key], Robot.updateOrientation);
		console.log("New robot: " + key);
		return true;
	}

	function parseObjectModel(key, val) {
		if (!isModelKey(key, "key_objects_prefix")) return false;

		const model = JSON.parse(val);
		addComponentToScene(GraphicsObject, objects, key, model);
		registerRedisUpdateCallback(model["key_pos"], key, objects[key], (object, val) => {
			const renderFrame = GraphicsObject.updatePosition(object, val);
			updateInteraction(key, object);
			return renderFrame;
		});
		if (model["key_ori"] !== "") {
			registerRedisUpdateCallback(model["key_ori"], key, objects[key], (object, val) => {
				const renderFrame = GraphicsObject.updateOrientation(object, val);
				updateInteraction(key, object);
				return renderFrame;
			});
		}
		if (model["key_scale"] !== "") {
			registerRedisUpdateCallback(model["key_scale"], key, objects[key], (object, val) => {
				const renderFrame = GraphicsObject.updateScale(object, val);
				updateInteraction(key, object);
				return renderFrame;
			});
		}
		if (model["key_matrix"] !== "") {
			registerRedisUpdateCallback(model["key_matrix"], key, objects[key], (object, val) => {
				const renderFrame = GraphicsObject.updateMatrix(object, val);
				updateInteraction(key, object);
				return renderFrame;
			});
		}
		console.log("New object: " + key);
		return true;
	}

	function parseTrajectoryModel(key, val) {
		if (!isModelKey(key, "key_trajectories_prefix")) return false;

		// Parse object model
		const model = JSON.parse(val);
		addComponentToScene(Trajectory, trajectories, key, model);
		registerRedisUpdateCallback(model["key_pos"], key, trajectories[key], Trajectory.appendPosition);
		console.log("New trajectory: " + key);
		return true;
	}

	function parseCameraModel(key, val) {
		if (!isModelKey(key, "key_cameras_prefix")) return false;

		// Parse object model
		const model = JSON.parse(val);
		addComponentToScene(Camera, cameras, key, model);
		registerRedisUpdateCallback(model["key_pos"], key, cameras[key], Camera.updatePosition);
		registerRedisUpdateCallback(model["key_ori"], key, cameras[key], Camera.updateOrientation);
		registerRedisUpdateCallback(model["key_intrinsic"], key, cameras[key], Camera.updateIntrinsic);
		registerRedisUpdateCallback(model["key_depth_image"], key, cameras[key], Camera.updateDepthImage);
		registerRedisUpdateCallback(model["key_color_image"], key, cameras[key], Camera.updateColorImage);
		console.log("New camera: " + key);
		return true;
	}

	function addComponentToScene(Component, components, key, model, callback) {
		let component = Component.create(model, (component) => {
			if (!(key in components) || components[key] != component) return;
			renderer.render(scene, camera);
			if (callback) {
				callback(component);
			}
		});

		// Delete old component
		if (key in components) {
			scene.remove(components[key]);
			delete components[key];
		}
		components[key] = component;

		scene.add(component);
		renderer.render(scene, camera);
	}

	function parseUpdateKeys(keyVals) {
		let renderFrame = false;
		for (const key in keyVals) {
			let val = keyVals[key];

			// Parse matrices (without converting to float)
			if (Redis.isNumeric(val)) {
				val = Redis.stringToMatrix(val, false);
			}

			// Call update event
			if (key in redisUpdateCallbacks) {
				for (const keyComponent in redisUpdateCallbacks[key]) {
					// console.log(key, keyComponent);
					const updateCallback = redisUpdateCallbacks[key][keyComponent];
					renderFrame = updateCallback(val) || renderFrame;
				}
			}

			// Update html
			if (typeof (val) === "object" && val.constructor === ArrayBuffer) {
				Redis.updateForm(key, null, false, true, false);
			} else {
				Redis.updateForm(key, val, true, true, true);
			}
		}
		return renderFrame;
	}

	function parseDeleteKeys(keys) {
		let renderFrame = false;

		keys.forEach((key) => {
			if (key in robots) {
				scene.remove(robots[key]);
				delete robots[key];
				unregisterRedisUpdateCallback(key);
				renderFrame = true;
			} else if (key in objects) {
				scene.remove(objects[key]);
				delete objects[key];
				unregisterRedisUpdateCallback(key);
				renderFrame = true;
			}
			Redis.deleteForm(key);
		});
		return renderFrame;
	}

	function getPosMouse(event) {
		const $canvas = $(renderer.domElement);
		const offset = $canvas.offset();
		return new THREE.Vector2((event.clientX - offset.left) / $canvas.width() * 2 - 1,
			-(event.clientY - offset.top) / $canvas.height() * 2 + 1);
	}

	function getAllMeshes() {
		let meshes = [];

		// Traverse down object tree
		const findMeshes = (obj) => {
			if (obj.type == "Mesh") {
				meshes.push(obj);
			}
			for (const child of obj.children) {
				findMeshes(child);
			}
		}

		// Find all robot meshes
		for (let key in robots) {
			findMeshes(robots[key]);
		}

		// Find all object meshes
		for (let key in objects) {
			findMeshes(objects[key]);
		}

		return meshes;
	}

	function getModifierKeys(event) {
		let keys = [];
		if (event.altKey) keys.push("alt");
		if (event.ctrlKey) keys.push("ctrl");
		if (event.metaKey) keys.push("meta");
		if (event.shiftKey) keys.push("shift");
		return keys;
	}

	function updateInteraction(key, bodies) {
		// Update body position in mouse drag line
		if (!lineMouseDrag || key !== interaction["key_object"]) return;

		let posClick = new THREE.Vector3();
		posClick.fromArray(interaction["pos_click_in_link"]);
		if (bodies.constructor === Array) {
			// Robot
			bodies[interaction["idx_link"]].localToWorld(posClick);
		} else {
			// Object
			bodies.localToWorld(posClick);
		}
		lineMouseDrag.array[0] = posClick.x;
		lineMouseDrag.array[1] = posClick.y;
		lineMouseDrag.array[2] = posClick.z;
		lineMouseDrag.needsUpdate = true;
	}

	function findIntersectedObject(intersect, objectMap, isEqual) {
		let object = intersect.object;
		while (object.parent) {
			for (let key in objectMap) {
				if (!isEqual) {
					if (objectMap[key] != object) continue;
					return [key, object];
				}
				if (isEqual(objectMap[key], object)) {
					return [key, object];
				}
			}
			object = object.parent;
		}
		return ["", null];
	}

	function handleInteraction(event) {
		$(this).focus();
		if (event.which != 1) return;
		if (getModifierKeys(event).length === 0) return;
		event.stopImmediatePropagation();

		// Cast ray from mouse
		if (!raycaster) raycaster = new THREE.Raycaster();
		const posMouseDown = getPosMouse(event);
		raycaster.setFromCamera(posMouseDown, camera);
		const intersects = raycaster.intersectObjects(getAllMeshes());
		if (intersects.length === 0) return;

		// Find intersected body
		const intersect = intersects[0];
		let keyVal = findIntersectedObject(intersect, robots,
			(robot, object) => robot.redisgl.bodies.includes(object));
		if (!keyVal[0]) {
			keyVal = findIntersectedObject(intersect, objects)
		}
		if (!keyVal[0]) return;

		const key_object = keyVal[0];
		const object = keyVal[1];
		interaction["key_object"] = key_object;
		if (key_object in robots) {
			interaction["idx_link"] = robots[key_object].redisgl.bodies.indexOf(object);
		}
		let posClickInBody = intersect.point.clone();
		object.worldToLocal(posClickInBody);
		interaction["pos_click_in_link"] = posClickInBody.toArray();
		interaction["modifier_keys"] = getModifierKeys(event);

		// Create mouse line
		let lineGeometry = new THREE.BufferGeometry();
		let lineVertices = new Float32Array([
			intersect.point.x, intersect.point.y, intersect.point.z,
			intersect.point.x, intersect.point.y, intersect.point.z
		]);
		lineGeometry.setAttribute("position", new THREE.BufferAttribute(lineVertices, 3));
		let lineMaterial = new THREE.LineBasicMaterial({ color: 0xffffff });
		let line = new THREE.Line(lineGeometry, lineMaterial);
		scene.add(line);

		// Compute distance from camera to intersect
		let lookat = controls.target.clone().sub(camera.position).normalize();
		let vecCameraToIntersect = intersect.point.clone();
		vecCameraToIntersect.sub(camera.position);
		const distLookat = lookat.dot(vecCameraToIntersect);

		const mouseMove = (e) => {
			// Get mouse world position
			const posMouseInCamera = getPosMouse(e);
			let posMouse = new THREE.Vector3(posMouseInCamera.x, posMouseInCamera.y, 0.5);
			posMouse.unproject(camera);

			// Set distance between mouse point and camera
			camera.worldToLocal(posMouse);
			posMouse.multiplyScalar(-distLookat / posMouse.z);
			camera.localToWorld(posMouse);

			// Update mouse point
			lineMouseDrag = line.geometry.attributes.position;
			lineMouseDrag.array[3] = posMouse.x;
			lineMouseDrag.array[4] = posMouse.y;
			lineMouseDrag.array[5] = posMouse.z;
			lineMouseDrag.needsUpdate = true;

			// Send Redis keys
			interaction.pos_mouse_in_world = posMouse.toArray();
			Redis.sendAjax("SET", KEY_INTERACTION, interaction);
			Redis.updateForm(KEY_INTERACTION, JSON.stringify(interaction));

			renderer.render(scene, camera);
		};
		const mouseUp = (e) => {
			$(document).off("mousemove", mouseMove);
			$(document).off("mouseup", mouseUp);
			lineMouseDrag = null;
			scene.remove(line);
			interaction.key_object = "";
			interaction.idx_link = 0;
			interaction.pos_click_in_link = [0, 0, 0];
			interaction.pos_mouse_in_world = [0, 0, 0];
			interaction.modifier_keys = [];
			Redis.sendAjax("SET", KEY_INTERACTION, interaction);
			Redis.updateForm(KEY_INTERACTION, JSON.stringify(interaction));
			renderer.render(scene, camera);
		}
		$(document).on("mousemove", mouseMove);
		$(document).on("mouseup", mouseUp);
	}

	function initGraphics() {

		var width = window.innerWidth - $("#sidebar").width();
		var height = window.innerHeight;  // - $("#plotly").height() - 4;

		camera = new THREE.PerspectiveCamera(50, width / height, 0.01, 100);
		camera.position.set(1.25, -1.25, 1);
		camera.up.set(0, 0, 1);
		camera.updateProjectionMatrix();

		scene = new THREE.Scene();

		renderer = new THREE.WebGLRenderer({ antialias: true });
		renderer.setSize(width, height);
		$("#threejs").html(renderer.domElement);

		$(renderer.domElement).on("mousedown", handleInteraction);
		$(renderer.domElement).attr("tabindex", -1);
		$(renderer.domElement).on("focusin", () => {
			$(document).on("keydown", keyDown);
			$(document).on("keyup", keyUp);
		}).on("focusout", () => {
			$(document).off("keydown", keyDown);
			$(document).off("keyup", keyUp);
			keyUp();
		});

		function keyDown(e) {
			if (e.key != interaction.key_down) {
				interaction.key_down = e.key;
				Redis.sendAjax("SET", KEY_INTERACTION, interaction);
				Redis.updateForm(KEY_INTERACTION, JSON.stringify(interaction));
			}
		}
		function keyUp() {
			interaction.key_down = "";
			Redis.sendAjax("SET", KEY_INTERACTION, interaction);
			Redis.updateForm(KEY_INTERACTION, JSON.stringify(interaction));
		}
		Redis.sendAjax("SET", KEY_INTERACTION, interaction);

		controls = new THREE.OrbitControls(camera, renderer.domElement);
		controls.enableKeys = false;
		camera.updateProjectionMatrix();
		// Redis.addForm(KEY_CAMERA_TARGET, [controls.target.toArray()], true, false, false, (key, val) => {
		// 	controls.target.fromArray(val[0]);
		// 	controls.update();
		// 	renderer.render(scene, camera);
		// });
		// Redis.addForm(KEY_CAMERA_POS, [controls.object.position.toArray()], true, false, false, (key, val) => {
		// 	console.log(val[0]);
		// 	camera.position.fromArray(val[0]);
		// 	camera.updateProjectionMatrix();
		// 	controls.update();
		// 	renderer.render(scene, camera);
		// });
		controls.addEventListener("change", function() {
			renderer.render(scene, camera);
			// Redis.updateForm(KEY_CAMERA_TARGET, [controls.target.toArray()]);
			// Redis.updateForm(KEY_CAMERA_POS, [controls.object.position.toArray()]);
		});

		// Redis.addForm(KEY_TRAJ_RESET, null, true, false, false, (key, val) => {
		// 	console.log("Reset trajectory");
		// 	for (const key in trajectories) {
		// 		Trajectory.reset(trajectories[key]);
		// 	}
		// 	renderer.render(scene, camera);
		// });
		// Redis.addForm(KEY_AXES_VISIBLE, [[0]], true, false, false, (key, val) => {
		// 	if (val[0][0] === 0) {
		// 		console.log("Hide axes");
		// 	} else {
		// 		console.log("Show axes");
		// 	}
		// });

		var grid = new THREE.GridHelper(1, 10);
		grid.rotation.x = Math.PI / 2;
		scene.add(grid);
		scene.add(Graphics.axes(AXIS_SIZE, AXIS_WIDTH));

		var light = new THREE.AmbientLight(0xffffff, 0.4);
		scene.add(light);

		light = new THREE.PointLight(0xffffff, 0.8);
		light.position.set(1, -1, 1);
		scene.add(light);

		light = new THREE.PointLight(0xffffff, 0.8);
		light.position.set(-1, 1, 1);
		scene.add(light);

		renderer.render(scene, camera);
	}

	$(window).resize(() => {
		const width = window.innerWidth - $("#sidebar").width();
		const height = window.innerHeight;
		// const height = $("#threejs").height() - 4;
		// $("#plotly").height(window.innerHeight - $("#threejs").height());
		camera.aspect = width / height;
		camera.updateProjectionMatrix();
		renderer.setSize(width, height);
		renderer.render(scene, camera);
	});
	// $("body").on("resize", ".ui-resizable", () => {
	// 	const width = window.innerWidth - $("#sidebar").width();
	// 	const height = $("#threejs").height() - 4;
	// 	$("#plotly").height(window.innerHeight - $("#threejs").height());
	// 	camera.aspect = width / height;
	// 	camera.updateProjectionMatrix();
	// 	renderer.setSize(width, height);
	// 	renderer.render(scene, camera);
	// });

	// $("#threejs").on("mousemove", function(e) {
	//     var offset = $("#threejs").offset();
	//     mouse.x = (e.clientX - offset.left) / $("#threejs").width() * 2 - 1;
	//     mouse.y = -(e.clientY - offset.top) / $("#threejs").height() * 2 + 1;
	// });

	// Copy values to clipboard
	$(document).on("click", "input.copy", function(e) {
		e.preventDefault();

		// Get val
		var $form = $(this).closest("form");
		var val = Redis.matrixToString(Redis.getMatrix($form));

		// Create temporary input to copy to clipboard
		var $temp = $("<input>");
		$("body").append($temp);
		$temp.val(val).select();
		document.execCommand("copy");
		$temp.remove();
	});

	// Copy values to clipboard
	$(document).on("click", "input.del", function(e) {
		e.preventDefault();

		// Get val
		var $form = $(this).closest("form");
		var key = $form.attr("data-key");
		Redis.sendAjax("DEL", key, "", true);

	});

	// $(".col-split > div:first-child").resizable({
	// 	handles: "e"
	// });

	// $(".row-split > div:first-child").resizable({
	// 	handles: "s"
	// });

});
