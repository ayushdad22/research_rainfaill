const CELL = { south: 53.00, north: 53.25, west: -6.50, east: -6.25 };

let SAMPLE = 10;
const MESH_SUBDIV = 150;
const PLANE_SIZE = 11;
const GAP = 7;

const stage = document.getElementById('stage');
const canvas = document.getElementById('c');

const W = () => stage.clientWidth;
const H = () => stage.clientHeight;

const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.setSize(W(), H());

const scene = new THREE.Scene();

const camera = new THREE.PerspectiveCamera(45, W() / H(), 0.1, 1000);
scene.add(new THREE.AmbientLight(0xffffff, 0.7));

const sun = new THREE.DirectionalLight(0xffffff, 1.1);
sun.position.set(12, 20, 8);
scene.add(sun);

const fill = new THREE.DirectionalLight(0xbcd0e0, 0.35);
fill.position.set(-10, 6, -12);
scene.add(fill);

// ---------------- Camera ----------------
let spherical = { theta: 0.6, phi: 1.0, r: 30 };

function updateCam() {
  const { theta, phi, r } = spherical;
  camera.position.set(
    r * Math.sin(phi) * Math.sin(theta),
    r * Math.cos(phi),
    r * Math.sin(phi) * Math.cos(theta)
  );
  camera.lookAt(0, -1, 0);
}
updateCam();

let dragging = false, lx = 0, ly = 0;
canvas.addEventListener('mousedown', e => { dragging = true; lx = e.clientX; ly = e.clientY; });
window.addEventListener('mouseup', () => dragging = false);
window.addEventListener('mousemove', e => {
  if (!dragging) return;
  spherical.theta -= (e.clientX - lx) * 0.008;
  spherical.phi = Math.max(0.25, Math.min(1.45, spherical.phi + (e.clientY - ly) * 0.008));
  lx = e.clientX; ly = e.clientY;
  updateCam();
});
canvas.addEventListener('wheel', e => {
  spherical.r = Math.max(14, Math.min(60, spherical.r + e.deltaY * 0.03));
  updateCam();
  e.preventDefault();
}, { passive: false });

// ---------------- Status ----------------
const statusText = document.getElementById('status-text');
function setStatus(t) { if (statusText) statusText.textContent = t; }

// ---------------- Noise ----------------
function makeFbm(seed, octaves, lacunarity, gain, frequency, amplitude) {
  function hash(x, y) {
    let h = Math.sin(x * 127.1 + y * 311.7 + seed * 53.7) * 43758.5453;
    return h - Math.floor(h);
  }
  function smooth(t) { return t * t * (3 - 2 * t); }
  function valueNoise(x, y) {
    const xi = Math.floor(x), yi = Math.floor(y);
    const xf = x - xi, yf = y - yi;
    const tl = hash(xi, yi), tr = hash(xi + 1, yi);
    const bl = hash(xi, yi + 1), br = hash(xi + 1, yi + 1);
    const u = smooth(xf), v = smooth(yf);
    const top = tl + (tr - tl) * u;
    const bot = bl + (br - bl) * u;
    return (top + (bot - top) * v) * 2 - 1;
  }
  return function (x, y) {
    let amp = amplitude, freq = frequency, sum = 0, norm = 0;
    for (let o = 0; o < octaves; o++) {
      sum += valueNoise(x * freq, y * freq) * amp;
      norm += amp; amp *= gain; freq *= lacunarity;
    }
    return sum / (norm || 1);
  };
}

// ---------------- Elevation loading ----------------
let fbmDetail = null;
let elevGrid = null;
let minE = 0, maxE = 1;

async function loadElevation() {
  try {
    const res = await fetch('elevation.json');
    if (res.ok) {
      const data = await res.json();
      if (data.sample) SAMPLE = data.sample;
      setStatus('Loaded elevation.json');
      setSource('SRTM (cached)');
      return data.elevations;
    }
  } catch (e) {}

  setStatus('Loading live SRTM...');
  const url = 'https://api.opentopodata.org/v1/srtm30m?locations=' + buildLocationString();
  try {
    const res = await fetch(url);
    const data = await res.json();
    if (data.status === 'OK') {
      setSource('SRTM (live)');
      return data.results.map(r => r.elevation ?? 0);
    }
  } catch (e) {}

  setStatus('Synthetic fallback');
  setSource('synthetic');
  return syntheticElevation();
}

function buildLocationString() {
  const locs = [];
  for (let r = 0; r < SAMPLE; r++)
    for (let c = 0; c < SAMPLE; c++) {
      const lat = CELL.south + (CELL.north - CELL.south) * (r / (SAMPLE - 1));
      const lon = CELL.west + (CELL.east - CELL.west) * (c / (SAMPLE - 1));
      locs.push(lat.toFixed(5) + ',' + lon.toFixed(5));
    }
  return locs.join('|');
}

function syntheticElevation() {
  const out = [];
  for (let r = 0; r < SAMPLE; r++)
    for (let c = 0; c < SAMPLE; c++) {
      const x = c / (SAMPLE - 1), y = r / (SAMPLE - 1);
      const peak1 = 700 * Math.exp(-(((x - 0.35) ** 2 + (y - 0.55) ** 2) / 0.04));
      const peak2 = 500 * Math.exp(-(((x - 0.65) ** 2 + (y - 0.3) ** 2) / 0.05));
      const ridge = 180 * Math.sin(x * 6) * Math.cos(y * 4);
      out.push(Math.max(20, peak1 + peak2 + ridge + 90));
    }
  return out;
}

// ---------------- Stats display ----------------
function setSource(s) { const el = document.getElementById('src'); if (el) el.textContent = s; }
function showStats(grid) {
  const mean = grid.reduce((a, b) => a + b, 0) / grid.length;
  const set = (id, v) => { const el = document.getElementById(id); if (el) el.textContent = Math.round(v) + ' m'; };
  set('min-elev', minE);
  set('max-elev', maxE);
  set('mean-elev', mean);
}

// ---------------- Colour ----------------
function elevToColor(t) {
  const stops = [
    [0.00, [45, 90, 61]], [0.35, [82, 110, 55]], [0.60, [120, 95, 60]],
    [0.82, [150, 130, 95]], [1.00, [216, 200, 160]]
  ];
  let a = stops[0], b = stops[stops.length - 1];
  for (let i = 0; i < stops.length - 1; i++)
    if (t >= stops[i][0] && t <= stops[i + 1][0]) { a = stops[i]; b = stops[i + 1]; break; }
  const f = (t - a[0]) / (b[0] - a[0] || 1);
  return [
    (a[1][0] + (b[1][0] - a[1][0]) * f) / 255,
    (a[1][1] + (b[1][1] - a[1][1]) * f) / 255,
    (a[1][2] + (b[1][2] - a[1][2]) * f) / 255
  ];
}

// ---------------- Height functions ----------------
const LEFT_X = -(PLANE_SIZE / 2 + GAP / 2);
const RIGHT_X = (PLANE_SIZE / 2 + GAP / 2);

let detailStrength = 0.15;
let detailFrequency = 2.0;
let slopeBoost = 1.0;
let vexFactor = 3.0;

function rebuildNoise() { fbmDetail = makeFbm(1337, 5, 2.0, 0.5, 0.6 * detailFrequency, 1.0); }

function realHeight(u, v) {
  const fx = u * (SAMPLE - 1), fy = v * (SAMPLE - 1);
  const x0 = Math.floor(fx), y0 = Math.floor(fy);
  const x1 = Math.min(x0 + 1, SAMPLE - 1), y1 = Math.min(y0 + 1, SAMPLE - 1);
  const dx = fx - x0, dy = fy - y0;
  const g = (r, c) => elevGrid[r * SAMPLE + c];
  const top = g(y0, x0) * (1 - dx) + g(y0, x1) * dx;
  const bot = g(y1, x0) * (1 - dx) + g(y1, x1) * dx;
  return top * (1 - dy) + bot * dy;
}

function baseHeight(u, v) {
  const norm = (realHeight(u, v) - minE) / (maxE - minE || 1);
  const spanKm = (maxE - minE) / 1000;
  return norm * spanKm * vexFactor * 2.2;
}

function combinedHeight(u, v, wx, wz) {
  const norm = (realHeight(u, v) - minE) / (maxE - minE || 1);
  let detail = fbmDetail(wx + 100, wz + 100);
  const slopeFactor = 1 + slopeBoost * norm;
  detail *= detailStrength * slopeFactor;
  return baseHeight(u, v) + detail;
}

// ---------------- Build terrain ----------------
let rawGroup = null, enhGroup = null;

// view state (restored)
let wireOn = false, sidesOn = true, rotateOn = false, smoothShade = true;

function buildSides(offsetX, N, heightFn) {
  const baseY = -3;
  const verts = [], cols = [];
  const half = PLANE_SIZE / 2, step = PLANE_SIZE / N;
  const soil = [0.55, 0.47, 0.34];
  function addQuad(ax, ay, az, bx, by, bz) {
    verts.push(ax, ay, az, bx, by, bz, bx, baseY, bz);
    verts.push(ax, ay, az, bx, baseY, bz, ax, baseY, az);
    for (let k = 0; k < 6; k++) cols.push(soil[0], soil[1], soil[2]);
  }
  for (let c = 0; c < N; c++) {
    const x0 = -half + c * step, x1 = -half + (c + 1) * step;
    const u0 = (x0 + half) / PLANE_SIZE, u1 = (x1 + half) / PLANE_SIZE;
    addQuad(x0, heightFn(u0, 0, x0 + offsetX, -half), -half, x1, heightFn(u1, 0, x1 + offsetX, -half), -half);
    addQuad(x1, heightFn(u1, 1, x1 + offsetX, half), half, x0, heightFn(u0, 1, x0 + offsetX, half), half);
  }
  for (let r = 0; r < N; r++) {
    const z0 = -half + r * step, z1 = -half + (r + 1) * step;
    const v0 = (z0 + half) / PLANE_SIZE, v1 = (z1 + half) / PLANE_SIZE;
    addQuad(-half, heightFn(0, v1, -half + offsetX, z1), z1, -half, heightFn(0, v0, -half + offsetX, z0), z0);
    addQuad(half, heightFn(1, v0, half + offsetX, z0), z0, half, heightFn(1, v1, half + offsetX, z1), z1);
  }
  const sg = new THREE.BufferGeometry();
  sg.setAttribute('position', new THREE.Float32BufferAttribute(verts, 3));
  sg.setAttribute('color', new THREE.Float32BufferAttribute(cols, 3));
  sg.computeVertexNormals();
  const m = new THREE.Mesh(sg, new THREE.MeshLambertMaterial({ vertexColors: true, side: THREE.DoubleSide }));
  const cap = new THREE.Mesh(
    new THREE.PlaneGeometry(PLANE_SIZE, PLANE_SIZE).rotateX(Math.PI / 2),
    new THREE.MeshLambertMaterial({ color: 0x6b5a42 }));
  cap.position.y = baseY;
  m.add(cap);
  return m;
}

function buildTerrainGroup(offsetX, subdiv, heightFn, faceted) {
  const group = new THREE.Group();

  const geo = new THREE.PlaneGeometry(PLANE_SIZE, PLANE_SIZE, subdiv, subdiv);
  geo.rotateX(-Math.PI / 2);
  const pos = geo.attributes.position;
  const colors = [];
  for (let i = 0; i < pos.count; i++) {
    const x = pos.getX(i), z = pos.getZ(i);
    const u = (x + PLANE_SIZE / 2) / PLANE_SIZE;
    const v = (z + PLANE_SIZE / 2) / PLANE_SIZE;
    pos.setY(i, heightFn(u, v, x + offsetX, z));
    const norm = (realHeight(u, v) - minE) / (maxE - minE || 1);
    const c = elevToColor(Math.min(1, Math.max(0, norm)));
    colors.push(c[0], c[1], c[2]);
  }
  geo.setAttribute('color', new THREE.Float32BufferAttribute(colors, 3));
  geo.computeVertexNormals();

  // faceted (flat) shading only applies to the raw side when smooth shading is OFF
  const flat = faceted && !smoothShade;
  const mesh = new THREE.Mesh(geo, new THREE.MeshLambertMaterial({ vertexColors: true, flatShading: flat }));
  mesh.userData.isMesh = true;
  group.add(mesh);

  // wireframe overlay
  const wm = new THREE.LineSegments(
    new THREE.WireframeGeometry(geo),
    new THREE.LineBasicMaterial({ color: 0x222222, transparent: true, opacity: 0.15 }));
  wm.visible = wireOn;
  wm.userData.isWire = true;
  group.add(wm);

  // block sides
  const sm = buildSides(offsetX, subdiv > 40 ? 80 : subdiv, heightFn);
  sm.visible = sidesOn;
  sm.userData.isSide = true;
  group.add(sm);

  group.position.x = offsetX;
  return group;
}

function rebuildAll() {
  if (rawGroup) scene.remove(rawGroup);
  if (enhGroup) scene.remove(enhGroup);
  // RAW: low res (data grid), faceted, no procedural detail
  rawGroup = buildTerrainGroup(LEFT_X, SAMPLE - 1, baseHeight, true);
  // ENHANCED: high res + procedural detail, smooth
  enhGroup = buildTerrainGroup(RIGHT_X, MESH_SUBDIV, combinedHeight, false);
  scene.add(rawGroup);
  scene.add(enhGroup);
}

// ---------------- UI: sliders ----------------
function bindSlider(id, valId, fn, fmt) {
  const el = document.getElementById(id);
  const out = document.getElementById(valId);
  if (!el) return;
  el.addEventListener('input', function () {
    const val = parseFloat(this.value);
    fn(val);
    if (out) out.textContent = fmt(val);
    if (elevGrid) rebuildAll();
  });
}
bindSlider('ds', 'ds-val', v => detailStrength = v, v => v.toFixed(2));
bindSlider('df', 'df-val', v => { detailFrequency = v; rebuildNoise(); }, v => v.toFixed(1));
bindSlider('sb', 'sb-val', v => slopeBoost = v, v => v.toFixed(1));
bindSlider('vex', 'vex-val', v => vexFactor = v, v => v.toFixed(1) + 'x');

// ---------------- UI: buttons (RESTORED) ----------------
function bindButton(id, handler) {
  const el = document.getElementById(id);
  if (el) el.addEventListener('click', function () { handler(this); });
}

bindButton('btn-wire', (btn) => {
  wireOn = !wireOn;
  [rawGroup, enhGroup].forEach(g => g && g.children.forEach(ch => { if (ch.userData.isWire) ch.visible = wireOn; }));
  btn.classList.toggle('on', wireOn);
});

bindButton('btn-sides', (btn) => {
  sidesOn = !sidesOn;
  [rawGroup, enhGroup].forEach(g => g && g.children.forEach(ch => { if (ch.userData.isSide) ch.visible = sidesOn; }));
  btn.classList.toggle('on', sidesOn);
});

bindButton('btn-rotate', (btn) => {
  rotateOn = !rotateOn;
  btn.classList.toggle('on', rotateOn);
});

bindButton('btn-smooth', (btn) => {
  smoothShade = !smoothShade;
  btn.classList.toggle('on', smoothShade);
  if (elevGrid) rebuildAll();   // rebuild so flat/smooth shading on the raw side updates
});

// ---------------- Animate ----------------
function animate() {
  requestAnimationFrame(animate);
  if (rotateOn) { spherical.theta += 0.0025; updateCam(); }
  renderer.render(scene, camera);
}
animate();

window.addEventListener('resize', () => {
  renderer.setSize(W(), H());
  camera.aspect = W() / H();
  camera.updateProjectionMatrix();
});

// ---------------- Init ----------------
(async function () {
  const grid = await loadElevation();
  elevGrid = grid;
  minE = Math.min(...grid);
  maxE = Math.max(...grid);
  showStats(grid);
  rebuildNoise();
  rebuildAll();
})();