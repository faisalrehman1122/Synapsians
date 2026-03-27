/* ═══════════════════════════════════════════════════════════
   UKW Exam Evaluator · app.js
   Three.js background + screen logic + question visualization
   ═══════════════════════════════════════════════════════════ */

// ── Three.js 3D background scene ──────────────────────────────
(function initThree() {
    const canvas = document.getElementById('bg');
    if (!canvas || typeof THREE === 'undefined') return;

    const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: false });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setClearColor(0xedf2fa, 1);

    const scene  = new THREE.Scene();
    scene.fog = new THREE.FogExp2(0xedf2fa, 0.007);

    const camera = new THREE.PerspectiveCamera(58, 1, 0.1, 500);
    camera.position.set(0, 16, 38);
    camera.lookAt(0, 0, -80);

    function resize() {
        const w = window.innerWidth, h = window.innerHeight;
        renderer.setSize(w, h);
        camera.aspect = w / h;
        camera.updateProjectionMatrix();
    }
    resize();
    window.addEventListener('resize', resize);

    // ════════════════════════════════════════════════════════
    // 1. SCROLLING GRID FLOOR
    //    Two overlapping grids tile seamlessly; both scroll
    //    toward the camera for the "moving floor" effect.
    // ════════════════════════════════════════════════════════
    const GRID_W = 280, GRID_D = 300, GRID_Y = -10;
    function makeGrid() {
        const geo = new THREE.PlaneGeometry(GRID_W, GRID_D, 28, 30);
        geo.rotateX(-Math.PI / 2);
        const mat = new THREE.MeshBasicMaterial({
            color: 0x134395, wireframe: true,
            transparent: true, opacity: 0.08,
        });
        return new THREE.Mesh(geo, mat);
    }
    const gridA = makeGrid();
    const gridB = makeGrid();
    gridA.position.set(0, GRID_Y, -60);
    gridB.position.set(0, GRID_Y, -60 - GRID_D);
    scene.add(gridA, gridB);
    let gridScrollSpeed = 4;

    // ════════════════════════════════════════════════════════
    // 2. WÜRZBURG RESIDENZ SILHOUETTE
    // ════════════════════════════════════════════════════════
    const residenzShape = new THREE.Shape();
    const sil = [
        [-50,0],[-50,5],[-42,5],[-42,7],[-38,7],[-38,10],[-34,10],
        [-34,8],[-26,8],[-26,11],[-22,12],[-18,9],[-14,9],[-14,12],
        [-10,13],[-7,15],[-4,16.5],[0,17.5],[4,16.5],[7,15],[10,13],
        [14,12],[14,9],[18,9],[22,12],[26,11],[26,8],[34,8],[34,10],
        [38,10],[38,7],[42,7],[42,5],[50,5],[50,0],
    ];
    residenzShape.moveTo(sil[0][0], sil[0][1]);
    for (let i = 1; i < sil.length; i++) residenzShape.lineTo(sil[i][0], sil[i][1]);
    residenzShape.closePath();
    const resMesh = new THREE.Mesh(
        new THREE.ShapeGeometry(residenzShape),
        new THREE.MeshBasicMaterial({
            color: 0x7aa3cc, transparent: true, opacity: 0.09,
            side: THREE.DoubleSide, depthWrite: false,
        })
    );
    resMesh.position.set(0, -2, -120);
    resMesh.scale.set(1.6, 1.0, 1);
    scene.add(resMesh);

    // ════════════════════════════════════════════════════════
    // 3. UKW LOGO WAVES — TubeGeometry for variable thickness
    //    Flat 2D ribbon shapes matching the SVG filled paths:
    //    • Blue swoosh: wide S-curve, variable width (thick centre, thin ends)
    //    • Green cross: thinner diagonal crossing stroke
    //    Built as ShapeGeometry — flat, facing camera, like the logo
    // ════════════════════════════════════════════════════════

    // Spline control points — blue swoosh S-curve matching logo
    function blueSwooshPts(xS, yS) {
        return [
            [-1.0,  0.0], [-0.85, 0.15], [-0.7,  0.35],
            [-0.55, 0.1], [-0.4, -0.3],  [-0.25,-0.7],
            [-0.1, -0.9], [ 0.0, -0.4],  [ 0.1,  0.5],
            [ 0.2,  1.0], [ 0.35, 0.6],  [ 0.45, 0.0],
            [ 0.55,-0.5], [ 0.65,-0.3],  [ 0.8,  0.3],
            [ 0.9,  0.35],[ 1.0,  0.1],
        ].map(p => new THREE.Vector2(p[0] * xS, p[1] * yS));
    }

    // Spline control points — green cross diagonal
    function greenCrossPts(xS, yS) {
        return [
            [-0.35, 0.9], [-0.2,  0.4], [-0.05,-0.1],
            [ 0.05,-0.7], [ 0.15,-0.9], [ 0.25,-0.5],
            [ 0.4,  0.1], [ 0.55, 0.6],
        ].map(p => new THREE.Vector2(p[0] * xS, p[1] * yS));
    }

    // Build a flat ribbon Shape from a 2D spline with variable width
    function makeRibbon(controlPts, maxWidth, color, opacity, yOff, zOff, phaseOff) {
        // Fit a smooth spline through the 2D control points
        const SAMPLES = 120;
        const curve = new THREE.SplineCurve(controlPts);
        const sampled = curve.getPoints(SAMPLES);

        // For each sample point, compute perpendicular normal & tapered width
        const upper = [], lower = [];
        for (let i = 0; i < sampled.length; i++) {
            const t = i / (sampled.length - 1);
            const w = maxWidth * (0.15 + 0.85 * Math.sin(t * Math.PI));

            let tx, ty;
            if (i === 0) {
                tx = sampled[1].x - sampled[0].x;
                ty = sampled[1].y - sampled[0].y;
            } else if (i === sampled.length - 1) {
                tx = sampled[i].x - sampled[i-1].x;
                ty = sampled[i].y - sampled[i-1].y;
            } else {
                tx = sampled[i+1].x - sampled[i-1].x;
                ty = sampled[i+1].y - sampled[i-1].y;
            }
            const len = Math.sqrt(tx*tx + ty*ty) || 1;
            const nx = -ty / len;
            const ny =  tx / len;

            upper.push(new THREE.Vector2(
                sampled[i].x + nx * w * 0.5,
                sampled[i].y + ny * w * 0.5
            ));
            lower.push(new THREE.Vector2(
                sampled[i].x - nx * w * 0.5,
                sampled[i].y - ny * w * 0.5
            ));
        }

        // Build shape: upper edge forward, lower edge backward
        const shape = new THREE.Shape();
        shape.moveTo(upper[0].x, upper[0].y);
        for (let i = 1; i < upper.length; i++) shape.lineTo(upper[i].x, upper[i].y);
        for (let i = lower.length - 1; i >= 0; i--) shape.lineTo(lower[i].x, lower[i].y);
        shape.closePath();

        const geo = new THREE.ShapeGeometry(shape);
        const mat = new THREE.MeshBasicMaterial({
            color, transparent: true, opacity,
            side: THREE.DoubleSide, depthWrite: false,
        });
        const mesh = new THREE.Mesh(geo, mat);
        mesh.position.set(0, yOff, zOff);
        scene.add(mesh);

        // Store base positions for per-frame vertex animation
        const pos = geo.attributes.position;
        const baseY = new Float32Array(pos.count);
        const baseX = new Float32Array(pos.count);
        let xMin = Infinity, xMax = -Infinity;
        for (let i = 0; i < pos.count; i++) {
            baseX[i] = pos.getX(i);
            baseY[i] = pos.getY(i);
            if (baseX[i] < xMin) xMin = baseX[i];
            if (baseX[i] > xMax) xMax = baseX[i];
        }

        return { mesh, mat, geo, baseX, baseY, xMin, xMax, baseOpacity: opacity, yOff, phaseOff: phaseOff || 0 };
    }

    // ── Create the ribbon waves ──
    const ribbons = [
        // Primary blue swoosh — prominent, close
        makeRibbon(blueSwooshPts(120, 8), 2.2, 0x134395, 0.18, 5,  -22, 0),
        // Green cross — thinner, medium depth
        makeRibbon(greenCrossPts(85, 7),  1.4, 0x00964E, 0.14, 3,  -35, Math.PI * 0.6),
        // Echo blue — farther back, fainter, wider span
        makeRibbon(blueSwooshPts(140, 6), 1.8, 0x4a7fd4, 0.07, 8,  -55, Math.PI * 1.1),
        // Echo green — deep back
        makeRibbon(greenCrossPts(100, 5), 1.0, 0x00964E, 0.05, -1, -70, Math.PI * 0.3),
    ];

    // ── Mouse tracking (smoothed) ──
    let mouseX = 0, mouseY = 0;   // normalised -1..+1
    let smoothMX = 0, smoothMY = 0;
    window.addEventListener('mousemove', e => {
        mouseX = (e.clientX / window.innerWidth)  * 2 - 1;
        mouseY = (e.clientY / window.innerHeight) * 2 - 1;
    });

    // Per-frame vertex update: calm ocean wave + cursor reactivity
    function animateRibbons(time, speed) {
        // Smooth mouse (lerp toward actual position)
        smoothMX += (mouseX - smoothMX) * 0.04;
        smoothMY += (mouseY - smoothMY) * 0.04;

        ribbons.forEach((r) => {
            const pos = r.geo.attributes.position;
            const xSpan = r.xMax - r.xMin || 1;

            for (let i = 0; i < pos.count; i++) {
                // Normalised X position along the ribbon (0..1)
                const xt = (r.baseX[i] - r.xMin) / xSpan;

                // ── Calm ocean: slow travelling wave ──
                // Primary wave: very slow, gentle amplitude
                const w1 = Math.sin(xt * Math.PI * 2.0 + time * speed * 0.8 + r.phaseOff) * 0.5;
                // Secondary harmonic: even slower, smoother
                const w2 = Math.sin(xt * Math.PI * 1.2 + time * speed * 0.5 + r.phaseOff * 1.3) * 0.25;

                // ── Cursor reactivity: gentle local bulge near mouse X ──
                // Map mouse X (-1..1) to ribbon xt space (0..1)
                const cursorXt = (smoothMX + 1) * 0.5;
                const dist = Math.abs(xt - cursorXt);
                // Gaussian-ish falloff: affects ~30% of ribbon width
                const cursorInfluence = Math.exp(-dist * dist * 20) * smoothMY * -0.6;

                pos.setY(i, r.baseY[i] + w1 + w2 + cursorInfluence);
            }
            pos.needsUpdate = true;
        });
    }

    // ════════════════════════════════════════════════════════
    // 4. PHASE-REACTIVE ANIMATION LOOP
    // ════════════════════════════════════════════════════════
    window._ukwPhase    = 'slides';
    window._ukwProgress = 0;

    let time = 0;
    let curGridOp  = 0.08, tGridOp  = 0.08;
    let curWvSpeed = 0.36, tWvSpeed = 0.36;
    let curWvOp    = 1.0,  tWvOp    = 1.0;
    let tGridScroll = 4;

    const blueC  = new THREE.Color(0x134395);
    const greenC = new THREE.Color(0x00964E);
    const midC   = new THREE.Color(0x4a7fd4);

    const camTargetPos = new THREE.Vector3(0, -5, 45);
    const camTargetLook = new THREE.Vector3(0, 30, -80);
    const curLookAt = new THREE.Vector3(0, 30, -80);

    function animate() {
        requestAnimationFrame(animate);
        const dt = 0.007;
        time += dt;

        const phase = window._ukwPhase;
        const prog  = (window._ukwProgress || 0) / 100;

        // Phase targets
        switch (phase) {
            case 'slides':
                tGridOp = 0.04; tWvSpeed = 0.18; tWvOp = 0.6; tGridScroll = 2; break;
            case 'uploading': case 'parsing':
                tGridOp = 0.09; tWvSpeed = 0.44; tWvOp = 1.05; tGridScroll = 6; break;
            case 'processing':
                tGridOp    = 0.09 + prog * 0.04;
                tWvSpeed   = 0.44 + prog * 0.18;
                tWvOp      = 1.05 + prog * 0.15;
                tGridScroll = 6 + prog * 6;
                break;
            case 'collating':
                tGridOp = 0.11; tWvSpeed = 0.50; tWvOp = 1.15; tGridScroll = 8; break;
            case 'complete':
                tGridOp = 0.09; tWvSpeed = 0.30; tWvOp = 1.0; tGridScroll = 3; break;
            default:
                tGridOp = 0.08; tWvSpeed = 0.36; tWvOp = 1.0; tGridScroll = 4;
        }

        // Lerp
        const L = 0.03;
        curGridOp  += (tGridOp  - curGridOp)  * L;
        curWvSpeed += (tWvSpeed - curWvSpeed) * L;
        curWvOp    += (tWvOp    - curWvOp)    * L;
        gridScrollSpeed += (tGridScroll - gridScrollSpeed) * L;

        // Grid opacity
        gridA.material.opacity = curGridOp;
        gridB.material.opacity = curGridOp;

        // ── GRID SCROLL toward camera ──
        const scrollDelta = gridScrollSpeed * dt;
        gridA.position.z += scrollDelta;
        gridB.position.z += scrollDelta;
        const wrapZ = 38 + GRID_D * 0.5;
        if (gridA.position.z > wrapZ) gridA.position.z = gridB.position.z - GRID_D;
        if (gridB.position.z > wrapZ) gridB.position.z = gridA.position.z - GRID_D;

        // ── Ribbon wave colour shift & opacity ──
        const colorProg = (phase === 'processing') ? prog
                        : (phase === 'complete')    ? 1.0 : 0.0;
        ribbons.forEach((tw, idx) => {
            const shift = Math.max(0, colorProg - idx * 0.1);
            const baseC = (idx % 2 === 1) ? greenC : (idx === 2 ? midC : blueC);
            tw.mat.color.copy(baseC).lerp(idx % 2 === 1 ? blueC : greenC, shift * 0.4);
            tw.mat.opacity = tw.baseOpacity * curWvOp;
        });

        // ── Animate ribbons: per-vertex flowing wave ──
        animateRibbons(time, curWvSpeed);
        ribbons.forEach((tw, idx) => {
            tw.mesh.rotation.y = Math.sin(time * curWvSpeed * 0.3 + idx) * 0.03;
        });

        // ── Camera breathing & panning ──
        if (phase === 'slides') {
            camTargetPos.set(Math.sin(time * 0.05) * 2, -2 + (time * 0.4), 45);
            camTargetLook.set(0, 25 + time * 0.2, -80);
        } else {
            camTargetPos.set(Math.sin(time * 0.10) * 2.5, 16 + Math.sin(time * 0.17) * 0.6, 38);
            camTargetLook.set(0, 0, -80);
        }

        camera.position.lerp(camTargetPos, L * 1.5);
        curLookAt.lerp(camTargetLook, L * 1.5);
        camera.lookAt(curLookAt);

        renderer.render(scene, camera);
    }

    animate();
})();


// ── App logic ──────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {

    const urlParams = new URLSearchParams(window.location.search);
    window._selectedModel = urlParams.get('model') === 'base' ? 'base' : 'finetuned';

    window.addEventListener('keydown', (e) => {
        if (e.key === 'Tab') {
            if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
            e.preventDefault();
            
            window._selectedModel = window._selectedModel === 'finetuned' ? 'base' : 'finetuned';
            
            const url = new URL(window.location);
            url.searchParams.set('model', window._selectedModel);
            window.history.replaceState({}, '', url);

            const indicator = document.getElementById('model-indicator');
            if (indicator) {
                indicator.textContent = window._selectedModel === 'finetuned' ? 'Finetuned Model (gpt-4o-exam-linter-v1)' : 'Base Model (gpt-4o)';
                indicator.classList.add('show');
                clearTimeout(window._modelIndicatorTimeout);
                window._modelIndicatorTimeout = setTimeout(() => {
                    indicator.classList.remove('show');
                }, 1500);
            }
        }
    });

    const dropZone   = document.getElementById('drop-zone');
    const fileInput  = document.getElementById('file-input');
    const evalBtn    = document.getElementById('evaluate-btn');
    const dlBtn      = document.getElementById('download-btn');
    const restartBtn = document.getElementById('restart-btn');
    const qRows      = document.getElementById('q-rows');
    const scanPhase  = document.getElementById('scan-phase');
    const scanMsg    = document.getElementById('scan-msg');
    const scanPct    = document.getElementById('scan-pct');

    const screens = {
        slides:   document.getElementById('screen-slides'),
        upload:   document.getElementById('screen-upload'),
        analysis: document.getElementById('screen-analysis'),
        done:     document.getElementById('screen-done'),
    };

    let file = null, blobUrl = null, evalName = null;

    // ── Screen transitions ────────────────────────────────────
    function goTo(name) {
        Object.entries(screens).forEach(([k, el]) => {
            if (k === name) {
                el.classList.remove('exit');
                el.classList.add('active');
            } else if (el.classList.contains('active')) {
                el.classList.add('exit');
                el.classList.remove('active');
            } else {
                el.classList.remove('exit', 'active');
            }
        });
    }

    // ── Drop zone ─────────────────────────────────────────────
    ['dragenter','dragover','dragleave','drop'].forEach(e =>
        dropZone.addEventListener(e, ev => { ev.preventDefault(); ev.stopPropagation(); }));
    ['dragenter','dragover'].forEach(e =>
        dropZone.addEventListener(e, () => dropZone.classList.add('dragover')));
    ['dragleave','drop'].forEach(e =>
        dropZone.addEventListener(e, () => dropZone.classList.remove('dragover')));

    dropZone.addEventListener('drop', e => pick(e.dataTransfer.files));
    dropZone.addEventListener('click', () => fileInput.click());
    dropZone.addEventListener('keydown', e => {
        if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); fileInput.click(); }
    });
    fileInput.addEventListener('change', function () { pick(this.files); });

    function pick(files) {
        if (!files.length) return;
        const f = files[0];
        if (!f.name.match(/\.docx?$/i)) { toast('Please upload a .docx file.', 'error'); return; }
        file = f;
        dropZone.classList.add('has-file');
        dropZone.querySelector('.dz-label').innerHTML = `<strong>${f.name}</strong>`;
        evalBtn.disabled = false;
    }

    // ── Question row helpers ───────────────────────────────────
    const qRowMap = {};
    let renderedCount = 0;

    // Always scroll the newest/active row into view smoothly
    function scrollRowIntoView(row) {
        row.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }

    function getOrCreateRow(q) {
        if (qRowMap[q]) return qRowMap[q];
        renderedCount++;
        const row = document.createElement('div');
        row.className = 'q-row';
        row.dataset.id = q;
        row.innerHTML = `
            <span class="q-num">Q${String(renderedCount).padStart(2,'0')}</span>
            <span class="q-type" data-type="">—</span>
            <div class="q-bar"><div class="q-bar-fill"></div></div>
        `;
        qRows.appendChild(row);
        qRowMap[q] = row;
        requestAnimationFrame(() => requestAnimationFrame(() => {
            row.classList.add('visible');
            scrollRowIntoView(row);
        }));
        return row;
    }

    function applyRows(questions) {
        if (!questions || !questions.length) return;
        questions.forEach(q => {
            const row = getOrCreateRow(q.id);
            const typeEl = row.querySelector('.q-type');
            if (typeEl && q.type) typeEl.textContent = q.type;

            row.classList.remove('active','done','error');
            if (q.status === 'active') {
                row.classList.add('active');
                scrollRowIntoView(row);
            } else if (q.status === 'done') {
                row.classList.add('done');
                row.querySelector('.q-bar-fill').style.width = '100%';
            } else if (q.status === 'error') {
                row.classList.add('error');
                row.querySelector('.q-bar-fill').style.width = '100%';
            }
        });
    }

    // Phase label copy
    const PHASE_LABELS = {
        idle:       'Ready',
        uploading:  'Uploading...',
        parsing:    'Processing Document...',
        processing: 'AI analyzing Questions',
        collating:  'Collating Feedback...',
        complete:   'Complete',
    };

    function applyStatus(data) {
        const phase    = data.phase    || 'idle';
        const progress = data.progress || 0;
        const message  = data.message  || '';

        scanPhase.textContent = PHASE_LABELS[phase] || phase;
        scanMsg.textContent   = message;
        scanPct.textContent   = Math.round(progress) + '%';

        window._ukwPhase    = phase;
        window._ukwProgress = progress;

        if (data.questions && data.questions.length) {
            applyRows(data.questions);
        }
    }

    // ── Analyse ───────────────────────────────────────────────
    evalBtn.addEventListener('click', async () => {
        if (!file) return;

        // ── Full UI reset ──
        const beam = qRows.querySelector('.scan-beam');
        qRows.innerHTML = '';
        if (beam) qRows.insertBefore(beam, qRows.firstChild);
        Object.keys(qRowMap).forEach(k => delete qRowMap[k]);
        renderedCount = 0;
        applyStatus({ phase: 'uploading', progress: 0, message: 'Establishing connection...' });

        goTo('analysis');
        window._ukwPhase = 'uploading';

        let polling = true;
        const loggedQs = new Set();
        const poll = async () => {
            if (!polling) return;
            try {
                const d = await (await fetch('http://127.0.0.1:8000/status')).json();
                applyStatus(d);
                if (d.debug_log && d.debug_log.length) {
                    d.debug_log.forEach(entry => {
                        if (loggedQs.has(entry.q)) return;
                        loggedQs.add(entry.q);
                        const label = `Q${entry.q} [${entry.type || '?'}]`;
                        const preview = entry.preview ? `\n   📄 ${entry.preview}` : '';
                        if (entry.error) {
                            const policyMatch = entry.error.match(/content_filter_result.*?'(\w+)':\s*\{'filtered': True,\s*'severity':\s*'(\w+)'/);
                            const policy = policyMatch ? policyMatch[1] : 'unknown';
                            const severity = policyMatch ? policyMatch[2] : '?';
                            console.warn(`⛔ ${label} — blocked by Azure content filter: ${policy} (severity: ${severity})${preview}`);
                        } else if (entry.comments > 0) {
                            console.log(`✅ ${label} — ${entry.comments} comment(s):${preview}`);
                            try {
                                const raw = JSON.parse(entry.raw_preview);
                                (raw.feedback_comments || []).forEach(c =>
                                    console.log(`   💬 "${c.exact_quote}" → ${c.comment}`)
                                );
                            } catch(_) {}
                        } else {
                            console.log(`✅ ${label} — no issues found`);
                        }
                    });
                }
            } catch (_) {}
            if (polling) setTimeout(poll, 300);
        };

        try {
            // Fire the POST first so the backend resets its state,
            // then start polling after a short delay.
            const fd = new FormData();
            fd.append('file', file);
            fd.append('model', window._selectedModel);
            const evalPromise = fetch('http://127.0.0.1:8000/evaluate', { method: 'POST', body: fd });

            // Give the backend time to receive the request and call progress.reset()
            setTimeout(() => { if (polling) poll(); }, 400);

            const resp = await evalPromise;
            polling = false;

            if (!resp.ok) {
                let errMsg = 'Server error ' + resp.status;
                try { const e = await resp.json(); errMsg = e.error || errMsg; } catch(_) {}
                throw new Error(errMsg);
            }

            const blob = await resp.blob();
            if (blobUrl) URL.revokeObjectURL(blobUrl);
            blobUrl  = URL.createObjectURL(blob);
            evalName = 'eval_' + file.name;

            applyStatus({ phase: 'complete', progress: 100, message: 'Done!' });
            window._ukwPhase = 'complete';

            // Force all remaining rows to "done" so every bar fills to 100%
            qRows.querySelectorAll('.q-row').forEach(row => {
                row.classList.remove('active', 'error');
                row.classList.add('done');
                row.querySelector('.q-bar-fill').style.width = '100%';
            });

            // Wait for the CSS bar-fill transition (0.7s) + breathing room
            await new Promise(r => setTimeout(r, 1400));
            goTo('done');

        } catch (err) {
            polling = false;
            window._ukwPhase = 'idle';
            console.error('[Evaluate] Backend error:', err);
            goTo('upload');
            toast('Error: ' + err.message, 'error');
        }
    });

    // ── Download ──────────────────────────────────────────────
    dlBtn.addEventListener('click', () => {
        if (!blobUrl) return;
        const a = document.createElement('a');
        a.href = blobUrl; a.download = evalName;
        document.body.appendChild(a); a.click(); document.body.removeChild(a);
    });

    // ── Restart ───────────────────────────────────────────────
    restartBtn.addEventListener('click', () => {
        file = null; fileInput.value = '';
        dropZone.classList.remove('has-file');
        dropZone.querySelector('.dz-label').innerHTML = `Drop <strong>.docx</strong> file here`;
        evalBtn.disabled = true;
        window._ukwPhase = 'idle';
        goTo('upload');
    });

    // ── Toast ──────────────────────────────────────────────────
    function toast(msg, type = 'info') {
        document.querySelector('.toast')?.remove();
        const t = Object.assign(document.createElement('div'), {
            className: `toast toast-${type}`,
            textContent: msg
        });
        document.body.appendChild(t);
        requestAnimationFrame(() => requestAnimationFrame(() => t.classList.add('toast-visible')));
        setTimeout(() => {
            t.classList.remove('toast-visible');
            t.addEventListener('transitionend', () => t.remove(), { once: true });
        }, 3500);
    }

    // ── Slide Navigation ───────────────────────────────────────
    let slideIndex = 0;
    const NUM_SLIDES = 2; // indices 0, 1, 2
    const slideEls = document.querySelectorAll('.slide');

    function updateSlides() {
        if (slideIndex > NUM_SLIDES) {
            window._ukwPhase = 'idle';
            goTo('upload');
        } else {
            slideEls.forEach((sl, i) => {
                if (i === slideIndex) sl.classList.add('slide-active');
                else sl.classList.remove('slide-active');
            });
        }
    }

    function handleSlideKey(e) {
        if (window._ukwPhase !== 'slides' && window._ukwPhase !== 'idle') return;
        if (['INPUT', 'TEXTAREA'].includes(e.target.tagName)) return;
        
        if (window._ukwPhase === 'slides') {
            if (e.key === 'ArrowRight' || e.key === ' ' || e.key === 'Enter') {
                e.preventDefault();
                slideIndex++;
                updateSlides();
            } else if (e.key === 'ArrowLeft') {
                e.preventDefault();
                slideIndex = Math.max(0, slideIndex - 1);
                updateSlides();
            }
        } else if (window._ukwPhase === 'idle' && e.key === 'ArrowLeft') {
            e.preventDefault();
            slideIndex = NUM_SLIDES;
            window._ukwPhase = 'slides';
            goTo('slides'); 
            updateSlides();
        }
    }

    document.addEventListener('keydown', handleSlideKey);

    // ── Boot ───────────────────────────────────────────────────
    if (window._ukwPhase === 'slides') {
        goTo('slides');
    } else {
        goTo('upload');
    }
});
