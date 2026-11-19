"use strict";

// The GPU receives only the current material boundary and native body poses.
// Anatomy overlays (legs, antennae and load silhouettes) are presentation.
const nestScene = (() => {
    const cross = (a, b) => [a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0]];
    const unit = a => { const r = Math.hypot(...a) || 1; return a.map(x => x/r); };
    const offset = (p, a, s) => p.map((x, i) => x + s*a[i]);
    const canvas = document.createElement("canvas");
    let gpu, unavailable = false;

    const lighting = `
        precision highp float;
        in vec3 world, normal, color;
        in float finish;
        out vec4 pixel;
        uniform float opacity;
        uniform vec3 eye;
        float grain(vec3 p){
          p=fract(p*0.2113+vec3(.1031,.11369,.13787));
          p+=dot(p,p.yzx+19.19);
          return fract((p.x+p.y)*p.z);
        }
        void main(){
          vec3 n=normalize(normal);
          if(finish<0. && dot(n,eye)<0.) discard;
          vec3 light=normalize(vec3(-.52,.84,-.32));
          float diffuse=max(0.,dot(n,light));
          float gloss=pow(max(0.,dot(n,normalize(light+eye))),24.);
          float m=grain(floor(world*41880.))*.08+grain(floor(world*4700.))*.13;
          float bed=sin((world.y+.00016*grain(floor(world*2600.)))*32700.)*.035;
          float texture=m+bed-.093;
          float f=finish<0.?1.+texture:1.;
          vec3 shade=color*((.55+.45*diffuse)*f);
          shade+=vec3(.44,.34,.26)*(gloss*max(0.,finish));
          pixel=vec4(shade,opacity);
        }`;

    function program(gl, geometry) {
        const source = geometry ? `
          layout(location=0) in vec3 p;
          layout(location=1) in vec3 n;
          layout(location=2) in vec3 tint;
          void main(){ world=p; normal=n; color=tint; finish=-1.;
            gl_Position=camera*vec4(world,1.); }` : `
          layout(location=0) in vec3 p;
          layout(location=1) in vec3 center;
          layout(location=2) in vec3 forward;
          layout(location=3) in vec3 up;
          layout(location=4) in vec3 axes;
          layout(location=5) in vec3 tint;
          layout(location=6) in float rough;
          void main(){
            mat3 frame=mat3(forward,up,cross(forward,up));
            world=center+frame*(axes*p); normal=frame*(p/axes);
            color=tint; finish=rough; gl_Position=camera*vec4(world,1.);
          }`;
        const compile = (type, text) => {
            const shader = gl.createShader(type);
            gl.shaderSource(shader, "#version 300 es\n" + text);
            gl.compileShader(shader);
            if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) throw Error(gl.getShaderInfoLog(shader));
            return shader;
        };
        const p = gl.createProgram();
        const vert = compile(gl.VERTEX_SHADER, `
          uniform mat4 camera;
          out vec3 world, normal, color;
          out float finish;
        ` + source);
        const frag = compile(gl.FRAGMENT_SHADER, lighting);
        gl.attachShader(p, vert); gl.attachShader(p, frag); gl.linkProgram(p);
        gl.deleteShader(vert); gl.deleteShader(frag);
        if (!gl.getProgramParameter(p, gl.LINK_STATUS)) throw Error(gl.getProgramInfoLog(p));
        return {p, camera: gl.getUniformLocation(p, "camera"), opacity: gl.getUniformLocation(p, "opacity"),
            eye: gl.getUniformLocation(p, "eye")};
    }

    function initialize() {
        const gl = canvas.getContext("webgl2", {alpha: true, antialias: true, depth: true});
        if (!gl) return null;
        const terrain = program(gl, true), anatomy = program(gl, false);
        const earth = gl.createVertexArray(), soil = gl.createBuffer();
        gl.bindVertexArray(earth); gl.bindBuffer(gl.ARRAY_BUFFER, soil);
        for (let i=0; i<3; i++) {
            gl.enableVertexAttribArray(i);
            gl.vertexAttribPointer(i, 3, gl.FLOAT, false, 36, i*12);
        }
        const organs = gl.createVertexArray(), instance = gl.createBuffer(), vertices = [];
        const point = (row, column) => {
            const lat = (row/10-.5)*Math.PI, lon = column*Math.PI/8;
            return [Math.cos(lat)*Math.cos(lon), Math.sin(lat), Math.cos(lat)*Math.sin(lon)];
        };
        for (let i=0; i<10; i++) for (let j=0; j<16; j++) {
            const a=point(i,j), b=point(i+1,j), c=point(i+1,j+1), d=point(i,j+1);
            vertices.push(...a,...b,...c,...a,...c,...d);
        }
        gl.bindVertexArray(organs);
        gl.bindBuffer(gl.ARRAY_BUFFER, gl.createBuffer());
        gl.bufferData(gl.ARRAY_BUFFER, new Float32Array(vertices), gl.STATIC_DRAW);
        gl.enableVertexAttribArray(0); gl.vertexAttribPointer(0, 3, gl.FLOAT, false, 12, 0);
        gl.bindBuffer(gl.ARRAY_BUFFER, instance);
        for (let i=1; i<=6; i++) {
            gl.enableVertexAttribArray(i);
            gl.vertexAttribPointer(i, i===6?1:3, gl.FLOAT, false, 64, (i-1)*12);
            gl.vertexAttribDivisor(i,1);
        }
        return {gl, terrain, anatomy, soil, earth, organs, instance, vertices:vertices.length/3};
    }

    function soilMesh(faces, groundY) {
        const facesData = (caps, cover) => {
            const vertices = [];
            for (const f of faces) {
                if (f.cap!==caps || caps && (Math.abs(f.points[0][1]-groundY)<1e-9)!==cover) continue;
                const normal = [0,0,0]; normal[f.axis] = f.sign;
                const color = f.material === 2 ? [.45,.44,.41] :
                    cover ? [.41,.41,.25] : f.cap ? [.55,.38,.24] : [.63,.45,.29];
                for (const i of [0,1,2,0,2,3]) vertices.push(...f.points[i],...normal,...color);
            }
            return vertices;
        };
        return [facesData(false,false), facesData(true,false), facesData(true,true)];
    }

    function putShape(buffer, center, forward, up, radii, color, finish) {
        buffer.push(...center,...forward,...up,...radii,...color,finish);
    }

    function bodyShapes(buffer, ant, time) {
        const body = ant.body;
        const at = ant.display_position_m || ant.position_m;
        const move = ant.display_motion;
        const heading = move && motionHeading(move,time);
        const up = body.up;
        const forward = heading && up[1] === 1 ? heading : body.forward;
        const right = cross(forward,up);
        const stages = {Egg:[.95,.88,.70], Larva:[.91,.79,.60], Pupa:[.82,.64,.43]};
        const color = stages[ant.stage] || (ant.caste==="Queen"?[.24,.15,.10]:[.30,.20,.13]);
        for (const [shift,...axes] of body.segments) putShape(buffer,offset(at,forward,shift),forward,up,axes,color,.65);
        if (ant.stage !== "Adult") return;
        const [head, trunk, abdomen] = body.segments;
        const thin = trunk[3]*.084;
        const stride = move?.progress>0 && move.progress<1 ? Math.sin((time-move.translates_ms)*.029) : 0;
        const inspecting = body.care && time>=body.care.began_ms &&
            ["Inspect brood","Clean brood","Feed brood","Pick up brood","Place brood","Close worker contact"].includes(body.care.act);
        const feelers = inspecting ? Math.sin((time-body.care.began_ms)*.025)*head[2]*.32 : 0;
        const link = (from,to,r) => {
            const vector=to.map((x,i)=>x-from[i]);
            const axis=unit(vector), side=unit(cross(axis,right));
            if (side.every(x=>!x)) return;
            putShape(buffer,offset(from,vector,.5),axis,side,[Math.hypot(...vector)*.57,r,r],color,.5);
        };
        for (const side of [-1,1]) {
            for (let i=0;i<3;i++) {
                const root = offset(offset(at,forward,trunk[0]+(.62-i*.6)*trunk[1]),right,side*trunk[3]*.67);
                const knee = offset(offset(root,right,side*trunk[3]*.95),forward,(1-i)*trunk[1]*.4);
                const toe = offset(offset(offset(knee,right,side*trunk[3]*.65),up,-trunk[2]*1.07),
                    forward,(1-i+side*(i===1?-1:1)*stride*.65)*trunk[1]*.63);
                link(root,knee,thin); link(knee,toe,thin*.69);
            }
            const base=offset(offset(at,forward,head[0]+head[1]*.54),right,side*head[3]*.4);
            const elbow=offset(offset(base,forward,head[1]*.48),right,side*head[3]*.94);
            const tip=offset(offset(offset(elbow,forward,head[1]*.76),right,side*head[3]*.39),up,feelers);
            link(base,elbow,thin*.46); link(elbow,tip,thin*.30);
        }
        putShape(buffer,offset(at,forward,abdomen[0]+abdomen[1]*.61),forward,up,
            [trunk[1]*.30,trunk[2]*.42,trunk[3]*.37],color,.6);
        if (ant.loaded && !body.held_id) {
            const cargo=offset(offset(at,forward,head[0]+head[1]*1.23),up,-head[2]*.24);
            putShape(buffer,cargo,forward,up,[head[1]*.49,head[2]*.58, head[3]*.53],
                ant.soil_load?[.66,.44,.25]:[.75,.64,.29],.28);
        }
    }

    function motionHeading(move,time) {
        const headings = [[1,0,0],[1,0,1],[0,0,1],[-1,0,1],[-1,0,0],[-1,0,-1],[0,0,-1],[1,0,-1],[0,1,0],[0,-1,0]];
        const before=move.heading, after=move.target_heading;
        if (!after) return null;
        if (!before || before>8 || after>8 || time>=move.translates_ms) return unit(headings[after-1]);
        const turn=((after-before+12)%8)-4;
        const fraction=Math.max(0,(time-move.begins_ms)/(move.translates_ms-move.begins_ms));
        const angle=(before-1+turn*fraction)*Math.PI/4;
        return [Math.cos(angle),0,Math.sin(angle)];
    }

    function piles(buffer, parcels) {
        const deposits=new Map();
        for (const parcel of parcels) {
            const key=parcel.position_m.join(",");
            const previous=deposits.get(key);
            deposits.set(key,{position:parcel.base_m || parcel.position_m, volume:parcel.volume_mm3+(previous?.volume||0)});
        }
        for (const {position,volume} of deposits.values()) if (volume>0) {
            // An ellipsoid with aspect 0.42 and the actual deposited volume.
            const radius=Math.cbrt(volume*1e-9/(4/3*Math.PI*.42));
            putShape(buffer,offset(position,[0,1,0],radius*.42),[1,0,0],[0,1,0],
                [radius,radius*.42,radius],[.62,.43,.29],.05);
        }
    }

    function draw(ctx, width, height, project, direction, faces, actors, contents, transparent, groundY, time) {
        if (unavailable) return false;
        try { gpu ||= initialize(); }
        catch (error) { console.warn("Nest lighting unavailable",error); unavailable=true; return false; }
        if (!gpu || gpu.gl.isContextLost()) { unavailable=true; return false; }
        const {gl, terrain, anatomy, soil, earth, organs, instance, vertices}=gpu;
        const ratio=Math.min(2,window.devicePixelRatio||1);
        if (canvas.width!==Math.round(width*ratio)) canvas.width=Math.round(width*ratio);
        if (canvas.height!==Math.round(height*ratio)) canvas.height=Math.round(height*ratio);
        const zero=project([0,0,0]);
        const camera=[];
        for (const axis of [[1,0,0],[0,1,0],[0,0,1]]) {
            const q=project(axis).map((x,i)=>x-zero[i]);
            camera.push(q[0]*2/width,-q[1]*2/height,-6*q[2],0);
        }
        camera.push(zero[0]*2/width-1,1-zero[1]*2/height,-6*zero[2],1);
        const use=(p, alpha=1) => {
            gl.useProgram(p.p); gl.uniformMatrix4fv(p.camera,false,camera);
            gl.uniform1f(p.opacity,alpha); gl.uniform3fv(p.eye,direction);
        };
        if (gpu.faces!==faces) {
            const sections=soilMesh(faces,groundY);
            gpu.counts=sections.map(s=>s.length/9); gpu.faces=faces;
            gl.bindBuffer(gl.ARRAY_BUFFER,soil);
            gl.bufferData(gl.ARRAY_BUFFER,new Float32Array(sections.flat()),gl.STATIC_DRAW);
        }
        gl.viewport(0,0,canvas.width,canvas.height);
        gl.clearColor(0,0,0,0); gl.clear(gl.COLOR_BUFFER_BIT|gl.DEPTH_BUFFER_BIT);
        gl.enable(gl.DEPTH_TEST); gl.enable(gl.BLEND);
        gl.blendFuncSeparate(gl.SRC_ALPHA,gl.ONE_MINUS_SRC_ALPHA,gl.ONE,gl.ONE_MINUS_SRC_ALPHA);
        gl.bindVertexArray(earth);
        const [walls,cut,cover]=gpu.counts;
        use(terrain); gl.drawArrays(gl.TRIANGLES,0,walls);
        gl.depthMask(!transparent);
        use(terrain,transparent?.18:1);
        gl.drawArrays(gl.TRIANGLES,walls,cut+cover);
        gl.depthMask(true);
        // A transparent stratum intentionally exposes real actors below the roof.
        if (transparent) gl.clear(gl.DEPTH_BUFFER_BIT);
        const data=[];
        piles(data,contents);
        for (const {ant} of actors) if (ant.body) bodyShapes(data,ant,time);
        gl.bindVertexArray(organs);
        gl.bindBuffer(gl.ARRAY_BUFFER,instance);
        gl.bufferData(gl.ARRAY_BUFFER,new Float32Array(data),gl.DYNAMIC_DRAW);
        use(anatomy); gl.drawArraysInstanced(gl.TRIANGLES,0,vertices,data.length/16);
        ctx.drawImage(canvas,0,0,width,height);
        return true;
    }
    return {draw};
})();
