/**
 * redis-web-gui.js
 *
 * Author: Toki Migimatsu
 * Created: December 2017
 */

function htmlForm(key, val, set, del) {
  set = false || set;
  del = false || del;
  var form = "<a name='" + key + "'></a><form data-key='" + key + "'><div class='keyval-card'>\n";
  form += "\t<div class='key-header'>\n";
  form += "\t\t<label>" + key + "</label>\n";
  form += "\t\t<div class='buttons'>\n";
  if (del) {
    form += "\t\t\t<input type='button' value='Del' class='del' title='Delete key from Redis'>\n";
  }
  form += "\t\t\t<input type='button' value='Copy' class='copy' title='Copy value to clipboard'>\n";
  if (set) {
    form += "\t\t\t<input type='submit' value='Set' title='Set values in Redis: <enter>'>\n";
  }
  form += "\t\t</div>\n";
  form += "\t</div>\n";
  form += "\t<div class='val-body'>\n";
  if (typeof(val) === "string") {
    form += "\t\t<div class='val-row'>\n";
    form += "\t\t\t<div class='val-string'>\n";
    form += "\t\t\t\t<textarea class='val'>" + val + "</textarea>\n";
    form += "\t\t\t</div>\n";
    form += "\t\t</div>\n";
  } else { // val should be a 2D array
    val.forEach(function(row, idx_row) {
      form += "\t\t<div class='val-row'>\n";
      row.forEach(function(el, idx) {
        var f = (Math.round(parseFloat(el) * 10000) / 10000).toString()
        form += "\t\t\t<input class='val' type='text' value='" + f + "'>\n";
      });
      form += "\t\t</div>\n";
    });
  }
  form += "\t</div>\n";
  form += "</div></form>\n";
  return form;
}

function redisFormExists(key) {
  let $form = $("form[data-key='" + key + "']");
  return $form.length > 0;
}

function addRedisForm(key, val, set, del, verbose, callback) {
  let $form = $("form[data-key='" + key + "']");

  $form = $(htmlForm(key, val, set, del)).hide();
  $form.on("submit", (e) => {
    e.preventDefault();

    ajaxSendRedis("SET", key, getMatrix($form), verbose);

    if (callback) {
      callback(key, val);
    }
  });

  var li = "<a href='#" + key + "' title='" + key + "'><li>" + key + "</li></a>";
  var $li = $(li).hide();

  // Find alphabetical ordering
  var keys = $("form").map(function() {
    return $(this).attr("data-key");
  }).get();
  var idx_key;
  for (idx_key = 0; idx_key < keys.length; idx_key++) {
    if (key < keys[idx_key]) break;
  }
  if (idx_key < keys.length) {
    $("form").eq(idx_key).before($form);
    $("#left-col a").eq(idx_key).before($li);
  } else {
    $("#sidebar-keys").append($form);
    $("#left-col ul").append($li)
  }
  $form.slideDown("normal");
  $li.slideDown("normal");
}

function updateRedisForm(key, val, set, del, verbose) {
  let $form = $("form[data-key='" + key + "']");
  if ($form.length === 0) {
    addRedisForm(key, val, set, del, verbose);
  }

  // Update string
  var $inputs = $form.find(".val");
  if (typeof(val) === "string") {
    $inputs.eq(0).val(val);
    return;
  }

  // Replace matrix if size has changed
  if (val.length * val[0].length != $inputs.length) {
    var key = $form.attr("data-key");
    var html = htmlForm(key, val);
    $form.html(html);
    return;
  }

  // Update matrix
  var i = 0;
  val.forEach(function(row) {
    row.forEach(function(el) {
      var f = (Math.round(parseFloat(el) * 10000) / 10000).toString()
      $inputs.eq(i).val(f);
      i++;
    });
  });
}

function deleteHtmlKey(key) {
  var $form = $("form[data-key='" + key + "']");
  if ($form.length == 0) return;
  $form.slideUp("normal", function() {
    $form.remove();
  });
}

function getMatrix($form) {
  if ($form.find("div.val-string").length > 0)
    return $form.find("textarea.val").val();
  return $form.find("div.val-row").map(function() {
    return [$(this).find("input.val").map(function() {
      return parseFloat($(this).val());
    }).get().filter(el => el !== "")];
  }).get();
}

function fillMatrix(matrix, num) {
  matrix.forEach(function(row) {
    row.forEach(function(el, idx) {
      row[idx] = num.toString();
    });
  });
}

function matrixToString(matrix) {
  if (typeof(matrix) === "string") return matrix;
  return matrix.map(function(row) {
    return row.join(" ");
  }).join("; ");
}

function matrixDim(val) {
  if (typeof(val) === "string") return "";
  return [val.length, val[0].length].toString();
}

// Send updated key-val pair via POST
function ajaxSendRedis(command, key, val, verbose) {
  var data = {};
  if (command == "DEL") {
    data[key] = "";
  } else if (command == "SET") {
    data[key] = JSON.stringify(val);
  } else {
    return;
  }

  if (verbose) {
    console.log(data);
  }

  $.ajax({
    method: "POST",
    url: "/" + command,
    data: data
  });
}

function axes(size, line_width, colors) {
  colors = colors || [0xff0000, 0x00ff00, 0x0000ff];

  var xyz = new THREE.Object3D();

  var x_material = new MeshLineMaterial({
    color: new THREE.Color(colors[0]),
    lineWidth: line_width
  });
  var x_geometry = new THREE.Geometry();
  x_geometry.vertices.push(new THREE.Vector3(0, 0, 0));
  x_geometry.vertices.push(new THREE.Vector3(size, 0, 0));
  var x_line = new MeshLine();
  x_line.setGeometry(x_geometry);
  var x = new THREE.Mesh(x_line.geometry, x_material)

  var y_material = new MeshLineMaterial({
    color: new THREE.Color(colors[1]),
    lineWidth: line_width
  });
  var y_geometry = new THREE.Geometry();
  y_geometry.vertices.push(new THREE.Vector3(0, 0, 0));
  y_geometry.vertices.push(new THREE.Vector3(0, size, 0));
  var y_line = new MeshLine();
  y_line.setGeometry(y_geometry);
  var y = new THREE.Mesh(y_line.geometry, y_material)

  var z_material = new MeshLineMaterial({
    color: new THREE.Color(colors[2]),
    lineWidth: line_width
  });
  var z_geometry = new THREE.Geometry();
  z_geometry.vertices.push(new THREE.Vector3(0, 0, 0));
  z_geometry.vertices.push(new THREE.Vector3(0, 0, size));
  var z_line = new MeshLine();
  z_line.setGeometry(z_geometry);
  var z = new THREE.Mesh(z_line.geometry, z_material)

  xyz.add(x);
  xyz.add(y);
  xyz.add(z);
  return xyz;
}

