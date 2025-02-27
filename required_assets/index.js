'use strict';

// Create viewer.
var viewer = new Marzipano.Viewer(document.getElementById('pano'));

// Set for equirectangular image
var geometry = new Marzipano.EquirectGeometry([{ width: 4000 }])

// `img_data` is base64 encoded jpg that is included in the html viewer file 
var source = Marzipano.ImageUrlSource.fromString(img_data)

var scene = viewer.createScene({
  geometry: geometry,
  source: source,
  view: new Marzipano.RectilinearView(
    { yaw: 0, fov: Math.PI * 2},
    Marzipano.RectilinearView.limit.traditional(8192, 140*Math.PI/180)),
    pinFirstLevel: true
})

// Display scene.
scene.switchTo();
