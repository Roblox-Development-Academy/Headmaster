import  "./style.scss";
import { Scene, WebGLRenderer, PerspectiveCamera, HemisphereLight } from 'three';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';


gsap.registerPlugin(ScrollTrigger);


const originalPath = window.location.pathname + window.location.search;
const history = window.history;
history.replaceState(history.state, '', window.location.pathname); // Hide query parameters
window.addEventListener('beforeunload', function(e) {
    history.pushState(history.state, '', originalPath);
    e.preventDefault();
    e.returnValue = "Are you sure? Changes you made will not be saved."
});

if (displayMode) {
    console.log("Opened in display mode");
    // TODO - Show an alert
}

const otherPronounsOption = document.querySelector("input[name=pronouns][value='']");
const otherPronounsText = document.querySelector("input[name=other_pronoun]")
otherPronounsText.addEventListener('focus', function() {
    otherPronounsOption.checked = true;
    otherPronounsText.required = true; // The above doesn't fire the event
});
document.querySelectorAll("input[name=pronouns]").forEach(function(input) {
    input.addEventListener('change', function() {
        if (input == otherPronounsOption)
            otherPronounsText.required = true;
        else
            otherPronounsText.required = false;
    })
});
let hasExtra = false; // Whether the applicant used the "Extra" field
const extraOptionsDiv = document.getElementById("extra_options");
const submitButton = document.getElementById("submit-btn");
const extraOptionsDivHeight = extraOptionsDiv.scrollHeight;
submitButton.style.transform = `translateY(-${extraOptionsDivHeight}px)`;
document.getElementById('extra').addEventListener('input', function() {
    if (hasExtra != (this.value != "")) {
        hasExtra = !hasExtra;
        extraOptionsDiv.style.transform = hasExtra ? "translateY(0)" : "translateY(-20px)";
        extraOptionsDiv.style.opacity = hasExtra ? "1" :"0";
        submitButton.style.transform = hasExtra ? "translateY(0)" : `translateY(-${extraOptionsDivHeight}px)`;
    }
});

const canvas = document.getElementById("3d-viewport");

const scene = new Scene();
const renderer = new WebGLRenderer({canvas, alpha: false});
// renderer.setClearColor( 0x000000, 0 ); // Make background transparent if above alpha is true
//renderer.physicallyCorrectLights = true;

const fov = 75;
const aspect = canvas.width / canvas.height;
const near = 0.1;
const far = 5;
const camera = new PerspectiveCamera(fov, aspect, near, far);

const skyColor = 0xB1E1FF;  // light blue
const groundColor = 0xB97A20;  // brownish orange
const intensity = 1;
const light = new HemisphereLight(skyColor, groundColor, intensity);
scene.add(light);

let needResize = false;

function resizeCanvas() {
    canvas.height = window.innerHeight;
    canvas.width = document.body.clientWidth;
    needResize = true;
}
resizeCanvas();
window.addEventListener('resize', resizeCanvas);

const loader = new GLTFLoader();
loader.load("/static/3d/Sincerity Bird.glb", (glb) => {
    scene.add(glb.scene);
});

let controls = new OrbitControls(camera, canvas);
camera.position.set(0, 0, 0);

function render() {
    if (needResize) {
        needResize = false;
        camera.aspect = canvas.width / canvas.height;
        camera.updateProjectionMatrix();
    }
    controls.update();
    renderer.render(scene, camera);
    requestAnimationFrame(render);
}
render();
