/******/ (() => { // webpackBootstrap
/******/ 	"use strict";
/******/ 	// The require scope
/******/ 	var __webpack_require__ = {};
/******/ 	
/************************************************************************/
/******/ 	/* webpack/runtime/make namespace object */
/******/ 	(() => {
/******/ 		// define __esModule on exports
/******/ 		__webpack_require__.r = (exports) => {
/******/ 			if(typeof Symbol !== 'undefined' && Symbol.toStringTag) {
/******/ 				Object.defineProperty(exports, Symbol.toStringTag, { value: 'Module' });
/******/ 			}
/******/ 			Object.defineProperty(exports, '__esModule', { value: true });
/******/ 		};
/******/ 	})();
/******/ 	
/************************************************************************/
var __webpack_exports__ = {};
/*!********************************!*\
  !*** ./web/src/date_select.js ***!
  \********************************/
__webpack_require__.r(__webpack_exports__);


let selectedDate = new Date();
let btn = document.getElementById("submit-btn");
let panel = btn.parentElement;

function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

async function disableInput() {
    if (this.checked)
        this.disabled = true;
    await sleep(100);
    document.querySelector(".datepicker-container").style.overflow = 'visible';
}

document.querySelector("input[type=checkbox]").addEventListener("change", disableInput);

btn.addEventListener("click", function() {
    fetch("/date-select/?user-id=" + userId, {
        method: "POST",
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            date: selectedDate.getTime() / 1000
        })
    });
    beginAnimation();
});

$(function(){
    let minDate = new Date();
    minDate.setHours(0, 0, 0, 0);
    let maxDate = new Date();
    maxDate.setDate(maxDate.getDate() + 60);
    $('#datepicker').datepicker({
        minDate: minDate,
        maxDate: maxDate,
        navTitles: {
            days: 'MM <i>yyyy</i>' // Remove the grammatically incorrect comma between month and year
        },
        onSelect: function(formattedDate, date, inst) {
            selectedDate = date;
            btn.style.transition = 'all 0.4s ease 0s';
            btn.style.opacity = 1;
            btn.style.boxShadow="0 0 5px #0ff";
            btn.removeAttribute("disabled");
        }
    })
})

const foreCanvas = document.getElementById('foreCanvas');
const backCanvas = document.getElementById('backCanvas');
const foreCtx = foreCanvas.getContext('2d');
const backCtx = backCanvas.getContext('2d');
let btnCtx;
let panelLoc = panel.getBoundingClientRect();
resizeCanvas();
window.addEventListener('resize', resizeCanvas, false);

let btnImg = new Image();
btnImg.src = '/static/submit-btn.png';


gsap.registerEffect({
    name: "fade",
    effect: (targets, config) => {
        return gsap.to(targets, {duration: config.duration, opacity: 0});
    },
    defaults: {duration: 2},
    extendTimeline: true
});

function resizeCanvas(e) {
    foreCanvas.height = backCanvas.height = window.innerHeight;
    foreCanvas.width = backCanvas.width = window.innerWidth;
}

function wrapText(context, text, x, y, maxWidth, lineHeight) {
    let words = text.split(' ');
    let line = '';

    for (let n = 0; n < words.length; n++) {
        let testLine = line + words[n] + ' ';
        let metrics = context.measureText(testLine);
        let testWidth = metrics.width;
        if (testWidth > maxWidth && n > 0) {
            context.fillText(line, x, y);
            line = words[n] + ' ';
            y += lineHeight;
        } else {
            line = testLine;
        }
    }
    context.fillText(line, x, y);
}

function beginAnimation() {
    gsap.effects.fade('.calendar-panel :not(button)');
    gsap.to('.calendar-panel', {webkitFilter: "brightness(0.5)", filter: "brightness(0.5)", duration: 2});

    let btnCanvas = document.createElement('canvas');
    let imgHeight = btnCanvas.height = btn.offsetHeight;
    let imgWidth = btnCanvas.width = btn.offsetWidth;
    let btnLoc = btn.getBoundingClientRect();
    btnCanvas.style.display = 'block';
    btnCanvas.style.margin = '30% auto 0 auto';
    btn.style.display = 'none';
    panel.appendChild(btnCanvas);
    btnCtx = btnCanvas.getContext('2d');
    foreCtx.font = "bold " + Math.floor(window.innerHeight / 9) + "px Helvetica, Arial, sans-serif";
    foreCtx.fillStyle = "#000000";
    let textPt = {
        x: panelLoc.x + 10,
        y: panelLoc.y + 10
    };
    wrapText(foreCtx, "You may return to Discord now", panelLoc.x + 20, panelLoc.y + 80, panel.offsetWidth - 20, 90);
    let textWidth = panel.offsetWidth;
    let textHeight = panel.offsetHeight;
    let textData = foreCtx.getImageData(textPt.x, textPt.y, textWidth, textHeight).data;
    let endPts = []; // The endpoints in the text for all the particles
    for (let y = 0; y < textHeight; y += gsap.utils.random(3, 5, 1))
        for (let x = 0; x < textWidth; x += gsap.utils.random(3, 5, 1))
            if (textData[(y * textWidth + x) * 4 - 1] == 255) // If it's completely opaque
                endPts.push({
                    x: textPt.x + x,
                    y: textPt.y + y
                });
    console.log("There are", endPts.length, "end points!");
    foreCtx.clearRect(textPt.x, textPt.y, textWidth, textHeight);
    foreCanvas.style.visibility = 'visible';
    btnCtx.drawImage(btnImg, 0, 0, imgWidth, imgHeight);
    let btnData = btnCtx.getImageData(0, 0, imgWidth, imgHeight).data;
    let particles = []
    let count = 0;
    let tl = gsap.timeline({
        onUpdate: () => {
            foreCtx.clearRect(0, 0, window.innerWidth, window.innerHeight);
            backCtx.clearRect(0, 0, window.innerWidth, window.innerHeight);
            particles.forEach(particle => particle.draw());
        },
        onComplete: () => console.log("Finished! There are", count, "particles!"),
    });

    let animateColumn = function(x) {
        let progress = {
            p: 0
        }
        tl.to(progress, {p: 2.0, duration: 3.2, ease: "power1.out",
            onStart: () => {
                btnCtx.clearRect(x, 0, imgWidth - x, imgHeight);
                let density = Math.ceil(imgHeight / (endPts.length / imgWidth));
                for (let y = 0; y < imgHeight && count < endPts.length; y += density) {
                    let index = (y * imgWidth + x) * 4;
                    particles.push(new Particle(btnLoc.x + x, btnLoc.y + y, btnData.slice(index, index + 4), endPts[count], progress));
                    count++;
                }
                if (x == 0 && count < endPts.length) // If it is the last column in the button, generate unlimited particles
                    animateColumn(0);
            }
        }, '<0.02');
    }

    for (let x = imgWidth - 1; x >= 0; x--) {
        animateColumn(x)
    }
}

function Particle(x, y, colorArr, endPt, progress) {
    this.color = "rgba(" + colorArr.join(',') + ")";
    this.ctx = foreCtx;
    this.curves = [
        {
            start: {
                x: x,
                y: y
            },
            ctrl1: {
                x: x + gsap.utils.random(60, 80, 1),
                y: y + gsap.utils.random(-30, 30, 1)
            },
            ctrl2: {
                x: x + 450,
                y: y + 50
            },
            end: {
                x: panelLoc.x + panel.offsetWidth + Math.random() * 40 + 50,
                y: panelLoc.y + panel.offsetHeight / 2
            }
        },
    ];
    this.curves.push({
        start: this.curves[0].end,
        ctrl1: {
            x: this.curves[0].end.x - (this.curves[0].ctrl2.x - this.curves[0].end.x),
            y: this.curves[0].end.y - (this.curves[0].ctrl2.y - this.curves[0].end.y)
        },
        ctrl2: {
            x: panelLoc.x - 800,
            y: endPt.y + 350
        },
        end: endPt
    });
    this.draw = () => {
        let percent = progress.p;
        let curve = (percent < 1 ? this.curves[0] : this.curves[1]);
        let p = (percent > 1 ? percent - 1 : percent);
        let x = CubicN(p, curve.start.x, curve.ctrl1.x, curve.ctrl2.x, curve.end.x);
        let y = CubicN(p, curve.start.y, curve.ctrl1.y, curve.ctrl2.y, curve.end.y);
        if (x > panelLoc.x + panel.offsetWidth + 15)
            this.ctx = backCtx;
        else if (x < panelLoc.x - 30)
            this.ctx = foreCtx;
        this.ctx.beginPath();
        this.ctx.fillStyle = this.color;
        this.ctx.arc(x, y, 2, 0, 2 * Math.PI);
        this.ctx.fill();
    };
}

function CubicN(pct, a, b, c, d) {
    var t2 = pct * pct;
    var t3 = t2 * pct;
    return a + (-a * 3 + pct * (3 * a - a * pct)) * pct
    + (3 * b + pct * (-6 * b + b * 3 * pct)) * pct
    + (c * 3 - c * 3 * pct) * t2
    + d * t3;
}
/******/ })()
;
//# sourceMappingURL=data:application/json;charset=utf-8;base64,eyJ2ZXJzaW9uIjozLCJzb3VyY2VzIjpbIndlYnBhY2s6Ly9oZWFkbWFzdGVyL3dlYnBhY2svYm9vdHN0cmFwIiwid2VicGFjazovL2hlYWRtYXN0ZXIvd2VicGFjay9ydW50aW1lL21ha2UgbmFtZXNwYWNlIG9iamVjdCIsIndlYnBhY2s6Ly9oZWFkbWFzdGVyLy4vd2ViL3NyYy9kYXRlX3NlbGVjdC5qcyJdLCJuYW1lcyI6W10sIm1hcHBpbmdzIjoiOztVQUFBO1VBQ0E7Ozs7O1dDREE7V0FDQTtXQUNBO1dBQ0Esc0RBQXNELGtCQUFrQjtXQUN4RTtXQUNBLCtDQUErQyxjQUFjO1dBQzdELEU7Ozs7Ozs7OztBQ05xQjs7QUFFckI7QUFDQTtBQUNBOztBQUVBO0FBQ0E7QUFDQTs7QUFFQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7O0FBRUE7O0FBRUE7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBLFNBQVM7QUFDVDtBQUNBO0FBQ0EsU0FBUztBQUNULEtBQUs7QUFDTDtBQUNBLENBQUM7O0FBRUQ7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQSxTQUFTO0FBQ1Q7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQSxLQUFLO0FBQ0wsQ0FBQzs7QUFFRDtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBOztBQUVBO0FBQ0E7OztBQUdBO0FBQ0E7QUFDQTtBQUNBLGlDQUFpQyxzQ0FBc0M7QUFDdkUsS0FBSztBQUNMLGVBQWUsWUFBWTtBQUMzQjtBQUNBLENBQUM7O0FBRUQ7QUFDQTtBQUNBO0FBQ0E7O0FBRUE7QUFDQTtBQUNBOztBQUVBLG1CQUFtQixrQkFBa0I7QUFDckM7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQSxTQUFTO0FBQ1Q7QUFDQTtBQUNBO0FBQ0E7QUFDQTs7QUFFQTtBQUNBO0FBQ0EsZ0NBQWdDLHdFQUF3RTs7QUFFeEc7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQSxvQkFBb0I7QUFDcEIsbUJBQW1CLGdCQUFnQjtBQUNuQyx1QkFBdUIsZUFBZTtBQUN0QztBQUNBO0FBQ0E7QUFDQTtBQUNBLGlCQUFpQjtBQUNqQjtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQSxTQUFTO0FBQ1Q7QUFDQSxLQUFLOztBQUVMO0FBQ0E7QUFDQTtBQUNBO0FBQ0EseUJBQXlCO0FBQ3pCO0FBQ0E7QUFDQTtBQUNBLCtCQUErQix3Q0FBd0M7QUFDdkU7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQSxTQUFTO0FBQ1Q7O0FBRUEsOEJBQThCLFFBQVE7QUFDdEM7QUFDQTtBQUNBOztBQUVBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQSxhQUFhO0FBQ2I7QUFDQTtBQUNBO0FBQ0EsYUFBYTtBQUNiO0FBQ0E7QUFDQTtBQUNBLGFBQWE7QUFDYjtBQUNBO0FBQ0E7QUFDQTtBQUNBLFNBQVM7QUFDVDtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQSxTQUFTO0FBQ1Q7QUFDQTtBQUNBO0FBQ0EsU0FBUztBQUNUO0FBQ0EsS0FBSztBQUNMO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBOztBQUVBO0FBQ0E7QUFDQTtBQUNBO0FBQ0E7QUFDQTtBQUNBO0FBQ0EsQyIsImZpbGUiOiJkYXRlX3NlbGVjdC5qcyIsInNvdXJjZXNDb250ZW50IjpbIi8vIFRoZSByZXF1aXJlIHNjb3BlXG52YXIgX193ZWJwYWNrX3JlcXVpcmVfXyA9IHt9O1xuXG4iLCIvLyBkZWZpbmUgX19lc01vZHVsZSBvbiBleHBvcnRzXG5fX3dlYnBhY2tfcmVxdWlyZV9fLnIgPSAoZXhwb3J0cykgPT4ge1xuXHRpZih0eXBlb2YgU3ltYm9sICE9PSAndW5kZWZpbmVkJyAmJiBTeW1ib2wudG9TdHJpbmdUYWcpIHtcblx0XHRPYmplY3QuZGVmaW5lUHJvcGVydHkoZXhwb3J0cywgU3ltYm9sLnRvU3RyaW5nVGFnLCB7IHZhbHVlOiAnTW9kdWxlJyB9KTtcblx0fVxuXHRPYmplY3QuZGVmaW5lUHJvcGVydHkoZXhwb3J0cywgJ19fZXNNb2R1bGUnLCB7IHZhbHVlOiB0cnVlIH0pO1xufTsiLCJpbXBvcnQgXCIuL3N0eWxlLnNjc3NcIlxyXG5cclxubGV0IHNlbGVjdGVkRGF0ZSA9IG5ldyBEYXRlKCk7XHJcbmxldCBidG4gPSBkb2N1bWVudC5nZXRFbGVtZW50QnlJZChcInN1Ym1pdC1idG5cIik7XHJcbmxldCBwYW5lbCA9IGJ0bi5wYXJlbnRFbGVtZW50O1xyXG5cclxuZnVuY3Rpb24gc2xlZXAobXMpIHtcclxuICAgIHJldHVybiBuZXcgUHJvbWlzZShyZXNvbHZlID0+IHNldFRpbWVvdXQocmVzb2x2ZSwgbXMpKTtcclxufVxyXG5cclxuYXN5bmMgZnVuY3Rpb24gZGlzYWJsZUlucHV0KCkge1xyXG4gICAgaWYgKHRoaXMuY2hlY2tlZClcclxuICAgICAgICB0aGlzLmRpc2FibGVkID0gdHJ1ZTtcclxuICAgIGF3YWl0IHNsZWVwKDEwMCk7XHJcbiAgICBkb2N1bWVudC5xdWVyeVNlbGVjdG9yKFwiLmRhdGVwaWNrZXItY29udGFpbmVyXCIpLnN0eWxlLm92ZXJmbG93ID0gJ3Zpc2libGUnO1xyXG59XHJcblxyXG5kb2N1bWVudC5xdWVyeVNlbGVjdG9yKFwiaW5wdXRbdHlwZT1jaGVja2JveF1cIikuYWRkRXZlbnRMaXN0ZW5lcihcImNoYW5nZVwiLCBkaXNhYmxlSW5wdXQpO1xyXG5cclxuYnRuLmFkZEV2ZW50TGlzdGVuZXIoXCJjbGlja1wiLCBmdW5jdGlvbigpIHtcclxuICAgIGZldGNoKFwiL2RhdGUtc2VsZWN0Lz91c2VyLWlkPVwiICsgdXNlcklkLCB7XHJcbiAgICAgICAgbWV0aG9kOiBcIlBPU1RcIixcclxuICAgICAgICBoZWFkZXJzOiB7XHJcbiAgICAgICAgICAgICdDb250ZW50LVR5cGUnOiAnYXBwbGljYXRpb24vanNvbidcclxuICAgICAgICB9LFxyXG4gICAgICAgIGJvZHk6IEpTT04uc3RyaW5naWZ5KHtcclxuICAgICAgICAgICAgZGF0ZTogc2VsZWN0ZWREYXRlLmdldFRpbWUoKSAvIDEwMDBcclxuICAgICAgICB9KVxyXG4gICAgfSk7XHJcbiAgICBiZWdpbkFuaW1hdGlvbigpO1xyXG59KTtcclxuXHJcbiQoZnVuY3Rpb24oKXtcclxuICAgIGxldCBtaW5EYXRlID0gbmV3IERhdGUoKTtcclxuICAgIG1pbkRhdGUuc2V0SG91cnMoMCwgMCwgMCwgMCk7XHJcbiAgICBsZXQgbWF4RGF0ZSA9IG5ldyBEYXRlKCk7XHJcbiAgICBtYXhEYXRlLnNldERhdGUobWF4RGF0ZS5nZXREYXRlKCkgKyA2MCk7XHJcbiAgICAkKCcjZGF0ZXBpY2tlcicpLmRhdGVwaWNrZXIoe1xyXG4gICAgICAgIG1pbkRhdGU6IG1pbkRhdGUsXHJcbiAgICAgICAgbWF4RGF0ZTogbWF4RGF0ZSxcclxuICAgICAgICBuYXZUaXRsZXM6IHtcclxuICAgICAgICAgICAgZGF5czogJ01NIDxpPnl5eXk8L2k+JyAvLyBSZW1vdmUgdGhlIGdyYW1tYXRpY2FsbHkgaW5jb3JyZWN0IGNvbW1hIGJldHdlZW4gbW9udGggYW5kIHllYXJcclxuICAgICAgICB9LFxyXG4gICAgICAgIG9uU2VsZWN0OiBmdW5jdGlvbihmb3JtYXR0ZWREYXRlLCBkYXRlLCBpbnN0KSB7XHJcbiAgICAgICAgICAgIHNlbGVjdGVkRGF0ZSA9IGRhdGU7XHJcbiAgICAgICAgICAgIGJ0bi5zdHlsZS50cmFuc2l0aW9uID0gJ2FsbCAwLjRzIGVhc2UgMHMnO1xyXG4gICAgICAgICAgICBidG4uc3R5bGUub3BhY2l0eSA9IDE7XHJcbiAgICAgICAgICAgIGJ0bi5zdHlsZS5ib3hTaGFkb3c9XCIwIDAgNXB4ICMwZmZcIjtcclxuICAgICAgICAgICAgYnRuLnJlbW92ZUF0dHJpYnV0ZShcImRpc2FibGVkXCIpO1xyXG4gICAgICAgIH1cclxuICAgIH0pXHJcbn0pXHJcblxyXG5jb25zdCBmb3JlQ2FudmFzID0gZG9jdW1lbnQuZ2V0RWxlbWVudEJ5SWQoJ2ZvcmVDYW52YXMnKTtcclxuY29uc3QgYmFja0NhbnZhcyA9IGRvY3VtZW50LmdldEVsZW1lbnRCeUlkKCdiYWNrQ2FudmFzJyk7XHJcbmNvbnN0IGZvcmVDdHggPSBmb3JlQ2FudmFzLmdldENvbnRleHQoJzJkJyk7XHJcbmNvbnN0IGJhY2tDdHggPSBiYWNrQ2FudmFzLmdldENvbnRleHQoJzJkJyk7XHJcbmxldCBidG5DdHg7XHJcbmxldCBwYW5lbExvYyA9IHBhbmVsLmdldEJvdW5kaW5nQ2xpZW50UmVjdCgpO1xyXG5yZXNpemVDYW52YXMoKTtcclxud2luZG93LmFkZEV2ZW50TGlzdGVuZXIoJ3Jlc2l6ZScsIHJlc2l6ZUNhbnZhcywgZmFsc2UpO1xyXG5cclxubGV0IGJ0bkltZyA9IG5ldyBJbWFnZSgpO1xyXG5idG5JbWcuc3JjID0gJy9zdGF0aWMvc3VibWl0LWJ0bi5wbmcnO1xyXG5cclxuXHJcbmdzYXAucmVnaXN0ZXJFZmZlY3Qoe1xyXG4gICAgbmFtZTogXCJmYWRlXCIsXHJcbiAgICBlZmZlY3Q6ICh0YXJnZXRzLCBjb25maWcpID0+IHtcclxuICAgICAgICByZXR1cm4gZ3NhcC50byh0YXJnZXRzLCB7ZHVyYXRpb246IGNvbmZpZy5kdXJhdGlvbiwgb3BhY2l0eTogMH0pO1xyXG4gICAgfSxcclxuICAgIGRlZmF1bHRzOiB7ZHVyYXRpb246IDJ9LFxyXG4gICAgZXh0ZW5kVGltZWxpbmU6IHRydWVcclxufSk7XHJcblxyXG5mdW5jdGlvbiByZXNpemVDYW52YXMoZSkge1xyXG4gICAgZm9yZUNhbnZhcy5oZWlnaHQgPSBiYWNrQ2FudmFzLmhlaWdodCA9IHdpbmRvdy5pbm5lckhlaWdodDtcclxuICAgIGZvcmVDYW52YXMud2lkdGggPSBiYWNrQ2FudmFzLndpZHRoID0gd2luZG93LmlubmVyV2lkdGg7XHJcbn1cclxuXHJcbmZ1bmN0aW9uIHdyYXBUZXh0KGNvbnRleHQsIHRleHQsIHgsIHksIG1heFdpZHRoLCBsaW5lSGVpZ2h0KSB7XHJcbiAgICBsZXQgd29yZHMgPSB0ZXh0LnNwbGl0KCcgJyk7XHJcbiAgICBsZXQgbGluZSA9ICcnO1xyXG5cclxuICAgIGZvciAobGV0IG4gPSAwOyBuIDwgd29yZHMubGVuZ3RoOyBuKyspIHtcclxuICAgICAgICBsZXQgdGVzdExpbmUgPSBsaW5lICsgd29yZHNbbl0gKyAnICc7XHJcbiAgICAgICAgbGV0IG1ldHJpY3MgPSBjb250ZXh0Lm1lYXN1cmVUZXh0KHRlc3RMaW5lKTtcclxuICAgICAgICBsZXQgdGVzdFdpZHRoID0gbWV0cmljcy53aWR0aDtcclxuICAgICAgICBpZiAodGVzdFdpZHRoID4gbWF4V2lkdGggJiYgbiA+IDApIHtcclxuICAgICAgICAgICAgY29udGV4dC5maWxsVGV4dChsaW5lLCB4LCB5KTtcclxuICAgICAgICAgICAgbGluZSA9IHdvcmRzW25dICsgJyAnO1xyXG4gICAgICAgICAgICB5ICs9IGxpbmVIZWlnaHQ7XHJcbiAgICAgICAgfSBlbHNlIHtcclxuICAgICAgICAgICAgbGluZSA9IHRlc3RMaW5lO1xyXG4gICAgICAgIH1cclxuICAgIH1cclxuICAgIGNvbnRleHQuZmlsbFRleHQobGluZSwgeCwgeSk7XHJcbn1cclxuXHJcbmZ1bmN0aW9uIGJlZ2luQW5pbWF0aW9uKCkge1xyXG4gICAgZ3NhcC5lZmZlY3RzLmZhZGUoJy5jYWxlbmRhci1wYW5lbCA6bm90KGJ1dHRvbiknKTtcclxuICAgIGdzYXAudG8oJy5jYWxlbmRhci1wYW5lbCcsIHt3ZWJraXRGaWx0ZXI6IFwiYnJpZ2h0bmVzcygwLjUpXCIsIGZpbHRlcjogXCJicmlnaHRuZXNzKDAuNSlcIiwgZHVyYXRpb246IDJ9KTtcclxuXHJcbiAgICBsZXQgYnRuQ2FudmFzID0gZG9jdW1lbnQuY3JlYXRlRWxlbWVudCgnY2FudmFzJyk7XHJcbiAgICBsZXQgaW1nSGVpZ2h0ID0gYnRuQ2FudmFzLmhlaWdodCA9IGJ0bi5vZmZzZXRIZWlnaHQ7XHJcbiAgICBsZXQgaW1nV2lkdGggPSBidG5DYW52YXMud2lkdGggPSBidG4ub2Zmc2V0V2lkdGg7XHJcbiAgICBsZXQgYnRuTG9jID0gYnRuLmdldEJvdW5kaW5nQ2xpZW50UmVjdCgpO1xyXG4gICAgYnRuQ2FudmFzLnN0eWxlLmRpc3BsYXkgPSAnYmxvY2snO1xyXG4gICAgYnRuQ2FudmFzLnN0eWxlLm1hcmdpbiA9ICczMCUgYXV0byAwIGF1dG8nO1xyXG4gICAgYnRuLnN0eWxlLmRpc3BsYXkgPSAnbm9uZSc7XHJcbiAgICBwYW5lbC5hcHBlbmRDaGlsZChidG5DYW52YXMpO1xyXG4gICAgYnRuQ3R4ID0gYnRuQ2FudmFzLmdldENvbnRleHQoJzJkJyk7XHJcbiAgICBmb3JlQ3R4LmZvbnQgPSBcImJvbGQgXCIgKyBNYXRoLmZsb29yKHdpbmRvdy5pbm5lckhlaWdodCAvIDkpICsgXCJweCBIZWx2ZXRpY2EsIEFyaWFsLCBzYW5zLXNlcmlmXCI7XHJcbiAgICBmb3JlQ3R4LmZpbGxTdHlsZSA9IFwiIzAwMDAwMFwiO1xyXG4gICAgbGV0IHRleHRQdCA9IHtcclxuICAgICAgICB4OiBwYW5lbExvYy54ICsgMTAsXHJcbiAgICAgICAgeTogcGFuZWxMb2MueSArIDEwXHJcbiAgICB9O1xyXG4gICAgd3JhcFRleHQoZm9yZUN0eCwgXCJZb3UgbWF5IHJldHVybiB0byBEaXNjb3JkIG5vd1wiLCBwYW5lbExvYy54ICsgMjAsIHBhbmVsTG9jLnkgKyA4MCwgcGFuZWwub2Zmc2V0V2lkdGggLSAyMCwgOTApO1xyXG4gICAgbGV0IHRleHRXaWR0aCA9IHBhbmVsLm9mZnNldFdpZHRoO1xyXG4gICAgbGV0IHRleHRIZWlnaHQgPSBwYW5lbC5vZmZzZXRIZWlnaHQ7XHJcbiAgICBsZXQgdGV4dERhdGEgPSBmb3JlQ3R4LmdldEltYWdlRGF0YSh0ZXh0UHQueCwgdGV4dFB0LnksIHRleHRXaWR0aCwgdGV4dEhlaWdodCkuZGF0YTtcclxuICAgIGxldCBlbmRQdHMgPSBbXTsgLy8gVGhlIGVuZHBvaW50cyBpbiB0aGUgdGV4dCBmb3IgYWxsIHRoZSBwYXJ0aWNsZXNcclxuICAgIGZvciAobGV0IHkgPSAwOyB5IDwgdGV4dEhlaWdodDsgeSArPSBnc2FwLnV0aWxzLnJhbmRvbSgzLCA1LCAxKSlcclxuICAgICAgICBmb3IgKGxldCB4ID0gMDsgeCA8IHRleHRXaWR0aDsgeCArPSBnc2FwLnV0aWxzLnJhbmRvbSgzLCA1LCAxKSlcclxuICAgICAgICAgICAgaWYgKHRleHREYXRhWyh5ICogdGV4dFdpZHRoICsgeCkgKiA0IC0gMV0gPT0gMjU1KSAvLyBJZiBpdCdzIGNvbXBsZXRlbHkgb3BhcXVlXHJcbiAgICAgICAgICAgICAgICBlbmRQdHMucHVzaCh7XHJcbiAgICAgICAgICAgICAgICAgICAgeDogdGV4dFB0LnggKyB4LFxyXG4gICAgICAgICAgICAgICAgICAgIHk6IHRleHRQdC55ICsgeVxyXG4gICAgICAgICAgICAgICAgfSk7XHJcbiAgICBjb25zb2xlLmxvZyhcIlRoZXJlIGFyZVwiLCBlbmRQdHMubGVuZ3RoLCBcImVuZCBwb2ludHMhXCIpO1xyXG4gICAgZm9yZUN0eC5jbGVhclJlY3QodGV4dFB0LngsIHRleHRQdC55LCB0ZXh0V2lkdGgsIHRleHRIZWlnaHQpO1xyXG4gICAgZm9yZUNhbnZhcy5zdHlsZS52aXNpYmlsaXR5ID0gJ3Zpc2libGUnO1xyXG4gICAgYnRuQ3R4LmRyYXdJbWFnZShidG5JbWcsIDAsIDAsIGltZ1dpZHRoLCBpbWdIZWlnaHQpO1xyXG4gICAgbGV0IGJ0bkRhdGEgPSBidG5DdHguZ2V0SW1hZ2VEYXRhKDAsIDAsIGltZ1dpZHRoLCBpbWdIZWlnaHQpLmRhdGE7XHJcbiAgICBsZXQgcGFydGljbGVzID0gW11cclxuICAgIGxldCBjb3VudCA9IDA7XHJcbiAgICBsZXQgdGwgPSBnc2FwLnRpbWVsaW5lKHtcclxuICAgICAgICBvblVwZGF0ZTogKCkgPT4ge1xyXG4gICAgICAgICAgICBmb3JlQ3R4LmNsZWFyUmVjdCgwLCAwLCB3aW5kb3cuaW5uZXJXaWR0aCwgd2luZG93LmlubmVySGVpZ2h0KTtcclxuICAgICAgICAgICAgYmFja0N0eC5jbGVhclJlY3QoMCwgMCwgd2luZG93LmlubmVyV2lkdGgsIHdpbmRvdy5pbm5lckhlaWdodCk7XHJcbiAgICAgICAgICAgIHBhcnRpY2xlcy5mb3JFYWNoKHBhcnRpY2xlID0+IHBhcnRpY2xlLmRyYXcoKSk7XHJcbiAgICAgICAgfSxcclxuICAgICAgICBvbkNvbXBsZXRlOiAoKSA9PiBjb25zb2xlLmxvZyhcIkZpbmlzaGVkISBUaGVyZSBhcmVcIiwgY291bnQsIFwicGFydGljbGVzIVwiKSxcclxuICAgIH0pO1xyXG5cclxuICAgIGxldCBhbmltYXRlQ29sdW1uID0gZnVuY3Rpb24oeCkge1xyXG4gICAgICAgIGxldCBwcm9ncmVzcyA9IHtcclxuICAgICAgICAgICAgcDogMFxyXG4gICAgICAgIH1cclxuICAgICAgICB0bC50byhwcm9ncmVzcywge3A6IDIuMCwgZHVyYXRpb246IDMuMiwgZWFzZTogXCJwb3dlcjEub3V0XCIsXHJcbiAgICAgICAgICAgIG9uU3RhcnQ6ICgpID0+IHtcclxuICAgICAgICAgICAgICAgIGJ0bkN0eC5jbGVhclJlY3QoeCwgMCwgaW1nV2lkdGggLSB4LCBpbWdIZWlnaHQpO1xyXG4gICAgICAgICAgICAgICAgbGV0IGRlbnNpdHkgPSBNYXRoLmNlaWwoaW1nSGVpZ2h0IC8gKGVuZFB0cy5sZW5ndGggLyBpbWdXaWR0aCkpO1xyXG4gICAgICAgICAgICAgICAgZm9yIChsZXQgeSA9IDA7IHkgPCBpbWdIZWlnaHQgJiYgY291bnQgPCBlbmRQdHMubGVuZ3RoOyB5ICs9IGRlbnNpdHkpIHtcclxuICAgICAgICAgICAgICAgICAgICBsZXQgaW5kZXggPSAoeSAqIGltZ1dpZHRoICsgeCkgKiA0O1xyXG4gICAgICAgICAgICAgICAgICAgIHBhcnRpY2xlcy5wdXNoKG5ldyBQYXJ0aWNsZShidG5Mb2MueCArIHgsIGJ0bkxvYy55ICsgeSwgYnRuRGF0YS5zbGljZShpbmRleCwgaW5kZXggKyA0KSwgZW5kUHRzW2NvdW50XSwgcHJvZ3Jlc3MpKTtcclxuICAgICAgICAgICAgICAgICAgICBjb3VudCsrO1xyXG4gICAgICAgICAgICAgICAgfVxyXG4gICAgICAgICAgICAgICAgaWYgKHggPT0gMCAmJiBjb3VudCA8IGVuZFB0cy5sZW5ndGgpIC8vIElmIGl0IGlzIHRoZSBsYXN0IGNvbHVtbiBpbiB0aGUgYnV0dG9uLCBnZW5lcmF0ZSB1bmxpbWl0ZWQgcGFydGljbGVzXHJcbiAgICAgICAgICAgICAgICAgICAgYW5pbWF0ZUNvbHVtbigwKTtcclxuICAgICAgICAgICAgfVxyXG4gICAgICAgIH0sICc8MC4wMicpO1xyXG4gICAgfVxyXG5cclxuICAgIGZvciAobGV0IHggPSBpbWdXaWR0aCAtIDE7IHggPj0gMDsgeC0tKSB7XHJcbiAgICAgICAgYW5pbWF0ZUNvbHVtbih4KVxyXG4gICAgfVxyXG59XHJcblxyXG5mdW5jdGlvbiBQYXJ0aWNsZSh4LCB5LCBjb2xvckFyciwgZW5kUHQsIHByb2dyZXNzKSB7XHJcbiAgICB0aGlzLmNvbG9yID0gXCJyZ2JhKFwiICsgY29sb3JBcnIuam9pbignLCcpICsgXCIpXCI7XHJcbiAgICB0aGlzLmN0eCA9IGZvcmVDdHg7XHJcbiAgICB0aGlzLmN1cnZlcyA9IFtcclxuICAgICAgICB7XHJcbiAgICAgICAgICAgIHN0YXJ0OiB7XHJcbiAgICAgICAgICAgICAgICB4OiB4LFxyXG4gICAgICAgICAgICAgICAgeTogeVxyXG4gICAgICAgICAgICB9LFxyXG4gICAgICAgICAgICBjdHJsMToge1xyXG4gICAgICAgICAgICAgICAgeDogeCArIGdzYXAudXRpbHMucmFuZG9tKDYwLCA4MCwgMSksXHJcbiAgICAgICAgICAgICAgICB5OiB5ICsgZ3NhcC51dGlscy5yYW5kb20oLTMwLCAzMCwgMSlcclxuICAgICAgICAgICAgfSxcclxuICAgICAgICAgICAgY3RybDI6IHtcclxuICAgICAgICAgICAgICAgIHg6IHggKyA0NTAsXHJcbiAgICAgICAgICAgICAgICB5OiB5ICsgNTBcclxuICAgICAgICAgICAgfSxcclxuICAgICAgICAgICAgZW5kOiB7XHJcbiAgICAgICAgICAgICAgICB4OiBwYW5lbExvYy54ICsgcGFuZWwub2Zmc2V0V2lkdGggKyBNYXRoLnJhbmRvbSgpICogNDAgKyA1MCxcclxuICAgICAgICAgICAgICAgIHk6IHBhbmVsTG9jLnkgKyBwYW5lbC5vZmZzZXRIZWlnaHQgLyAyXHJcbiAgICAgICAgICAgIH1cclxuICAgICAgICB9LFxyXG4gICAgXTtcclxuICAgIHRoaXMuY3VydmVzLnB1c2goe1xyXG4gICAgICAgIHN0YXJ0OiB0aGlzLmN1cnZlc1swXS5lbmQsXHJcbiAgICAgICAgY3RybDE6IHtcclxuICAgICAgICAgICAgeDogdGhpcy5jdXJ2ZXNbMF0uZW5kLnggLSAodGhpcy5jdXJ2ZXNbMF0uY3RybDIueCAtIHRoaXMuY3VydmVzWzBdLmVuZC54KSxcclxuICAgICAgICAgICAgeTogdGhpcy5jdXJ2ZXNbMF0uZW5kLnkgLSAodGhpcy5jdXJ2ZXNbMF0uY3RybDIueSAtIHRoaXMuY3VydmVzWzBdLmVuZC55KVxyXG4gICAgICAgIH0sXHJcbiAgICAgICAgY3RybDI6IHtcclxuICAgICAgICAgICAgeDogcGFuZWxMb2MueCAtIDgwMCxcclxuICAgICAgICAgICAgeTogZW5kUHQueSArIDM1MFxyXG4gICAgICAgIH0sXHJcbiAgICAgICAgZW5kOiBlbmRQdFxyXG4gICAgfSk7XHJcbiAgICB0aGlzLmRyYXcgPSAoKSA9PiB7XHJcbiAgICAgICAgbGV0IHBlcmNlbnQgPSBwcm9ncmVzcy5wO1xyXG4gICAgICAgIGxldCBjdXJ2ZSA9IChwZXJjZW50IDwgMSA/IHRoaXMuY3VydmVzWzBdIDogdGhpcy5jdXJ2ZXNbMV0pO1xyXG4gICAgICAgIGxldCBwID0gKHBlcmNlbnQgPiAxID8gcGVyY2VudCAtIDEgOiBwZXJjZW50KTtcclxuICAgICAgICBsZXQgeCA9IEN1YmljTihwLCBjdXJ2ZS5zdGFydC54LCBjdXJ2ZS5jdHJsMS54LCBjdXJ2ZS5jdHJsMi54LCBjdXJ2ZS5lbmQueCk7XHJcbiAgICAgICAgbGV0IHkgPSBDdWJpY04ocCwgY3VydmUuc3RhcnQueSwgY3VydmUuY3RybDEueSwgY3VydmUuY3RybDIueSwgY3VydmUuZW5kLnkpO1xyXG4gICAgICAgIGlmICh4ID4gcGFuZWxMb2MueCArIHBhbmVsLm9mZnNldFdpZHRoICsgMTUpXHJcbiAgICAgICAgICAgIHRoaXMuY3R4ID0gYmFja0N0eDtcclxuICAgICAgICBlbHNlIGlmICh4IDwgcGFuZWxMb2MueCAtIDMwKVxyXG4gICAgICAgICAgICB0aGlzLmN0eCA9IGZvcmVDdHg7XHJcbiAgICAgICAgdGhpcy5jdHguYmVnaW5QYXRoKCk7XHJcbiAgICAgICAgdGhpcy5jdHguZmlsbFN0eWxlID0gdGhpcy5jb2xvcjtcclxuICAgICAgICB0aGlzLmN0eC5hcmMoeCwgeSwgMiwgMCwgMiAqIE1hdGguUEkpO1xyXG4gICAgICAgIHRoaXMuY3R4LmZpbGwoKTtcclxuICAgIH07XHJcbn1cclxuXHJcbmZ1bmN0aW9uIEN1YmljTihwY3QsIGEsIGIsIGMsIGQpIHtcclxuICAgIHZhciB0MiA9IHBjdCAqIHBjdDtcclxuICAgIHZhciB0MyA9IHQyICogcGN0O1xyXG4gICAgcmV0dXJuIGEgKyAoLWEgKiAzICsgcGN0ICogKDMgKiBhIC0gYSAqIHBjdCkpICogcGN0XHJcbiAgICArICgzICogYiArIHBjdCAqICgtNiAqIGIgKyBiICogMyAqIHBjdCkpICogcGN0XHJcbiAgICArIChjICogMyAtIGMgKiAzICogcGN0KSAqIHQyXHJcbiAgICArIGQgKiB0MztcclxufSJdLCJzb3VyY2VSb290IjoiIn0=