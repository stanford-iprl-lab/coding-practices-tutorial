/**
 * graphics.js
 *
 * Copyright 2019. All Rights Reserved.
 *
 * Created: February 04, 2019
 * Authors: Toki Migimatsu
 */

function loadObj(dir, file) {
	return new Promise((resolve, reject) => {
		new THREE.OBJLoader()
			.setPath(dir)
			.load(file, (obj) => {
				if (obj.materialLibraries.length === 0) {
					resolve(obj);
					return;
				}

				// TODO: Support only one material resource for now
				var promise_mtl = new Promise((resolve, reject) => {
					var mtllib = obj.materialLibraries[0];
					new THREE.MTLLoader()
						.setPath(dir)
						.load(mtllib, (mtl) => {
							mtl.preload();
							resolve(mtl);
						}, null, reject);
				});

				// Reload obj
				promise_mtl.then((mtl) => {
					new THREE.OBJLoader()
						.setMaterials(mtl)
						.setPath(dir)
						.load(file, resolve, null, reject);
				});
			}, null, reject);
	});
}

function loadDae(dir, file) {
	return new Promise((resolve, reject) => {
		new THREE.ColladaLoader()
			.setPath(dir)
			.load(file, resolve, null, reject);
	})
}

export function parse(graphicsStruct, body, promises) {

	const T_to_parent = graphicsStruct["T_to_parent"];
	const geometryStruct = graphicsStruct["geometry"];
	const materialStruct = graphicsStruct["material"];
	const type = geometryStruct["type"];

	if (materialStruct["rgba"][3] == 0.) return;

	if (type == "mesh") {

		const meshFilename = geometryStruct["mesh"];
		let webapp = location.pathname.split("/").pop();
		webapp = webapp.substr(0, webapp.lastIndexOf("."));
		const dir = "resources/" + webapp + "/" + meshFilename.substr(0, meshFilename.lastIndexOf("/") + 1);
		const file = meshFilename.substr(meshFilename.lastIndexOf("/") + 1);
		const ext = meshFilename.substr(meshFilename.lastIndexOf(".") + 1);

		let promise;
		if (ext === "obj") {
			promise = loadObj(dir, file);
		} else if (ext === "dae") {
			promise = loadDae(dir, file);
		} else {
			console.error("Unsupported filetype: " + meshFilename);
			return;
		}

		promises.push(new Promise((resolve, reject) => {
			promise.then((mesh) => {
				let obj = mesh;
				if (!("quaternion" in mesh)) {
					obj = mesh.scene;
				}

				const quat = T_to_parent["ori"];
				obj.quaternion.set(quat["x"], quat["y"], quat["z"], quat["w"]);
				obj.position.fromArray(T_to_parent["pos"]);
				obj.scale.fromArray(geometryStruct["scale"]);
				body.add(obj);
				resolve();
			});
		}));

	} else if (type == "box") {

		let geometry = new THREE.BoxGeometry();
		let material = new THREE.MeshNormalMaterial();
		material.transparent = true;
		let box = new THREE.Mesh(geometry, material);
		body.add(box);

		box.material.opacity = materialStruct["rgba"][3];
		box.material.needsUpdate = true;
		const T_to_parent = graphicsStruct["T_to_parent"];
		const quat = T_to_parent["ori"];
		box.quaternion.set(quat["x"], quat["y"], quat["z"], quat["w"]);
		box.position.fromArray(T_to_parent["pos"]);
		box.scale.fromArray(geometryStruct["scale"]);

	} else if (type == "capsule") {

		let obj = new THREE.Object3D();

		let geometry = new THREE.CylinderGeometry(geometryStruct["radius"],
			geometryStruct["radius"],
			geometryStruct["length"],
			16, 1, true);
		let material = new THREE.MeshNormalMaterial();
		material.transparent = true;
		let cylinder = new THREE.Mesh(geometry, material);
		obj.add(cylinder);

		let ends = [];
		const thetaRanges = [[0., Math.PI / 2.], [Math.PI / 2., Math.PI]];
		for (let i = 0; i < 2; i++) {
			let geometry = new THREE.SphereGeometry(graphicsStruct.geometry.radius, 16, 16,
				0., Math.PI * 2.,
				thetaRanges[i][0], thetaRanges[i][1]);
			let material = new THREE.MeshNormalMaterial();
			material.transparent = true;
			ends.push(new THREE.Mesh(geometry, material));
			obj.add(ends[i]);
		}
		ends[0].position.setY(graphicsStruct.geometry.length / 2.);
		ends[1].position.setY(-graphicsStruct.geometry.length / 2.);

		const opacity = materialStruct["rgba"][3]
		cylinder.material.opacity = opacity;
		cylinder.material.needsUpdate = true;
		ends[0].material.opacity = opacity;
		ends[0].material.needsUpdate = true;
		ends[1].material.opacity = opacity;
		ends[1].material.needsUpdate = true;
		const T_to_parent = graphicsStruct["T_to_parent"];
		const quat = T_to_parent["ori"];
		obj.quaternion.set(quat["x"], quat["y"], quat["z"], quat["w"]);
		obj.position.fromArray(T_to_parent["pos"]);

		body.add(obj);

	} else if (graphicsStruct.geometry.type == "sphere") {

		let sphere;
		// if (body.children.length === 0) {
		let geometry = new THREE.SphereGeometry(1, 16, 16);
		let material = new THREE.MeshNormalMaterial();
		material.transparent = true;
		sphere = new THREE.Mesh(geometry, material);
		body.add(sphere);
		// } else {
		//   sphere = body.children[0];
		//   if (sphere.geometry.type != "SphereGeometry") {
		//     sphere.geometry.dispose();
		//     sphere.geometry = new THREE.SphereGeometry(1, 16, 16);
		//   }
		// }

		sphere.material.opacity = materialStruct["rgba"][3];
		sphere.material.needsUpdate = true;
		const T_to_parent = graphicsStruct["T_to_parent"];
		const quat = T_to_parent["ori"];
		sphere.quaternion.set(quat["x"], quat["y"], quat["z"], quat["w"]);
		sphere.position.fromArray(T_to_parent["pos"]);
		sphere.scale.setScalar(geometryStruct["radius"]);

	} else if (graphicsStruct.geometry.type == "cylinder") {

		let cylinder;
		// if (body.children.length === 0) {
		let geometry = new THREE.CylinderGeometry(1, 1, 1, 16);
		let material = new THREE.MeshNormalMaterial();
		material.transparent = true;
		cylinder = new THREE.Mesh(geometry, material);
		body.add(cylinder);
		// } else {
		//   cylinder = body.children[0];
		//   if (cylinder.geometry.type != "CylinderGeometry") {
		//     cylinder.geometry.dispose();
		//     cylinder.geometry = new THREE.CylinderGeometry(1, 1, 1, 16);
		//   }
		// }

		cylinder.material.opacity = materialStruct["rgba"][3];
		cylinder.material.needsUpdate = true;
		const quat = T_to_parent["ori"];
		cylinder.quaternion.set(quat["x"], quat["y"], quat["z"], quat["w"]);
		cylinder.position.fromArray(T_to_parent["pos"]);
		cylinder.scale.setScalar(geometryStruct["radius"]);
		cylinder.scale.setY(geometryStruct["length"]);

	}

}

export function axes(size, line_width, colors) {
	colors = colors || [0xff0000, 0x00ff00, 0x0000ff];

	let xyz = new THREE.Object3D();

	const x_material = new MeshLineMaterial({
		color: new THREE.Color(colors[0]),
		lineWidth: line_width
	});
	const x_vertices = new Float32Array([0, 0, 0, size, 0, 0]);
	const x_geometry = new THREE.BufferGeometry()
		.setAttribute("position", new THREE.BufferAttribute(x_vertices, 3));
	let x_line = new MeshLine();
	x_line.setGeometry(x_geometry);
	const x = new THREE.Mesh(x_line.geometry, x_material)

	const y_material = new MeshLineMaterial({
		color: new THREE.Color(colors[1]),
		lineWidth: line_width
	});
	const y_vertices = new Float32Array([0, 0, 0, 0, size, 0]);
	const y_geometry = new THREE.BufferGeometry()
		.setAttribute("position", new THREE.BufferAttribute(y_vertices, 3));
	let y_line = new MeshLine();
	y_line.setGeometry(y_geometry);
	const y = new THREE.Mesh(y_line.geometry, y_material)

	let z_material = new MeshLineMaterial({
		color: new THREE.Color(colors[2]),
		lineWidth: line_width
	});
	const z_vertices = new Float32Array([0, 0, 0, 0, 0, size]);
	const z_geometry = new THREE.BufferGeometry()
		.setAttribute("position", new THREE.BufferAttribute(z_vertices, 3));
	let z_line = new MeshLine();
	z_line.setGeometry(z_geometry);
	const z = new THREE.Mesh(z_line.geometry, z_material)

	xyz.add(x);
	xyz.add(y);
	xyz.add(z);
	return xyz;
}
