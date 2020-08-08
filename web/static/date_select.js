let selectedDate = new Date();
let btn = document.getElementById("submit-btn");
let panel = btn.parentElement;

function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

async function disableInput(elem) {
    if (elem.checked)
        elem.disabled = true;
    await sleep(100)
    document.querySelector(".datepicker-container").style.overflow = 'visible';
}

btn.addEventListener("click", function() {
    fetch("/date-select/?user-id=" + userId, {
        method: "POST",
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
foreCanvas.addEventListener('resize', resizeCanvas, false);
backCanvas.addEventListener('resize', resizeCanvas, false);

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