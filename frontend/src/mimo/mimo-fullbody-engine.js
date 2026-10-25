(function (global) {
  'use strict';
  const P = { light:'#D8C5F0', lilac:'#B99BDF', shade:'#9873C4', deep:'#8057AE', belly:'#FFF0DE', bellyShade:'#E8CDBF', peach:'#F4A08D', peachLight:'#FFD1B6', plum:'#41274F', iris:'#24152F' };
  const STATES = {
    ready: ['Siap latihan', 'Hai! Kita latihan ngobrol, yuk.'],
    listening: ['Mendengarkan', 'Aku mendengarkan. Sekarang giliranmu.'],
    speaking: ['Berbicara', 'Giliran Mimo mencontohkan pengucapannya.'],
    thinking: ['Berpikir', 'Sebentar, aku siapkan masukan untukmu.'],
    encourage: ['Coba lagi', 'Pelan-pelan saja. Aku temani kamu mencoba lagi.'],
    success: ['Berhasil', 'Yeay! Satu langkah lagi makin percaya diri.'],
    sleepy: ['Mengantuk', 'Hoaam… waktunya hampir habis.'],
    wrapup: ['Sebentar lagi', 'Waktunya hampir habis, yuk disimpulkan.']
  };
  const clamp = (x,a=0,b=1) => Math.max(a,Math.min(b,x));
  const smoothstep = x => { x=clamp(x); return x*x*(3-2*x); };
  // ONE rhythm drives everything: a 3.6 s breath. Gestures run at 2× (1.8 s) so they land on the same beat;
  // head, gills and tail use the same rhythm with a small delay (follow-through) instead of their own speeds.
  const BREATH_S = 3.6;
  const beat = (t,mult=1,delay=0) => Math.sin(t/BREATH_S*Math.PI*2*mult-delay);
  // calm syllable envelope (~3.6 syllables/s), shaped by a slow phrase swell
  const syllable = t => (.5-.5*Math.cos(t*Math.PI*2*3.6))*(.7+.3*beat(t,.5));
  function pose(state,t) {
    const p = { lift:beat(t)*1.5, lean:beat(t,1,.4)*.01, head:beat(t,1,.7)*.014, breath:beat(t)*.012,
      right:-.28+beat(t,1,.5)*.05, left:-.27+beat(t,1,.6)*.05, tail:beat(t,1,1.1)*.06,
      mouth:.08, smile:1, round:0, joy:0, gazeX:0, gazeY:0, brows:0, gills:.035,
      listen:0, speak:0, think:0, celebrate:0, drowsy:0, yawn:0 };
    if(state==='ready'){p.right=-1.9+beat(t,2)*.28+beat(t,4,.4)*.05;p.head=beat(t,1,.7)*.02;p.mouth=.18;}
    if(state==='listening'){p.head=-.105+beat(t,1,.7)*.015;p.lean=-.015;p.gazeX=-2;p.brows=.18;p.listen=1;p.gills=.05;p.right=-.43+beat(t,1,.5)*.05;p.left=-.3+beat(t,1,.6)*.05;}
    if(state==='speaking'){
      p.mouth=.22+.6*syllable(t);p.round=.45+.18*beat(t,2);p.speak=1;
      p.right=-1.05+beat(t,2)*.32;p.left=-.55+beat(t,2,Math.PI)*.16;p.head=beat(t,2,.6)*.02;p.gills=.055;
    }
    if(state==='thinking'){p.head=.07;p.right=-2.78+beat(t,2)*.05;p.left=-.32;p.gazeX=4;p.gazeY=-5;p.brows=.65;p.think=1;p.tail=beat(t,1,1.1)*.035;}
    // eyes stay fully open (no wink, no squint); lifted brows + smile carry the encouragement
    if(state==='encourage'){p.head=-.035+beat(t,2,.6)*.025;p.right=-1.45+beat(t,2)*.24;p.left=-.8+beat(t,2,.5)*.08;p.brows=.1;p.mouth=.15;}
    if(state==='success'){const b=.5-.5*Math.cos(t/BREATH_S*Math.PI*4);p.lift=-b*11;p.breath=.015*beat(t,2);p.right=-2.15+beat(t,2)*.18;p.left=-2.15+beat(t,2,Math.PI)*.18;p.joy=1;p.mouth=.72;p.celebrate=1;p.gills=.07;p.tail=beat(t,2,1)*.08;}
    // still listening (faint ear arcs), but heavy lids, a slow nod and a yawn every two breaths
    if(state==='sleepy'){const y=Math.max(0,beat(t,.5))**6;
      p.head=.06+beat(t,.5,.8)*.035-y*.05;p.lean=.012;p.drowsy=.5+.1*beat(t,.5,1.4)+y*.6;p.yawn=y;p.brows=-.15+y*.25;
      p.mouth=.06+y*.94;p.round=y*1.7;p.right=-.28-y*.5;p.left=-.27-y*.5;p.listen=.6;p.gills=.02;p.tail=beat(t,.5,1.1)*.04;}
    // still listening, one hand raised in a slow "wrap it up" wave on the breath rhythm
    if(state==='wrapup'){p.head=-.07+beat(t,1,.7)*.015;p.lean=-.01;p.gazeX=-2;p.brows=.3;p.mouth=.12;p.listen=.8;p.gills=.045;
      p.right=-2.0+beat(t,1)*.06;p.left=-.3+beat(t,1,.6)*.05;p.lift=beat(t)*1.5+beat(t,1,.3)*1.2;}
    return p;
  }
  // Blink: both eyes, regular rhythm, closes fast and opens a little slower.
  function blinkAt(t) {
    const period=4.6,close=.08,open=.14,x=(t+1.2)%period;
    if(x<close)return smoothstep(x/close);
    if(x<close+open)return 1-smoothstep((x-close)/open);
    return 0;
  }
  function create(canvas, options={}) {
    const c=canvas.getContext('2d');
    if(!c)throw new Error('Canvas 2D is unavailable');
    let current=null,velocity=null;
    function oval(x,y,rx,ry,fill) { c.fillStyle=fill;c.beginPath();c.ellipse(x,y,rx,ry,0,0,Math.PI*2);c.fill(); }
    function path(fill,draw) { c.beginPath();draw();c.fillStyle=fill;c.fill(); }
    function line(color,width,draw) { c.beginPath();draw();c.strokeStyle=color;c.lineWidth=width;c.lineCap='round';c.lineJoin='round';c.stroke(); }
    function linear(x0,y0,x1,y1,stops) {const g=c.createLinearGradient(x0,y0,x1,y1);for(const [at,color]of stops)g.addColorStop(at,color);return g;}
    function radial(x,y,r,stops) {const g=c.createRadialGradient(x,y,0,x,y,r);for(const [at,color]of stops)g.addColorStop(at,color);return g;}
    function glowOval(x,y,rx,ry,color) {c.save();c.translate(x,y);c.scale(rx,ry);oval(0,0,1,1,radial(0,0,1,[[0,color],[1,'rgba(255,240,230,0)']]));c.restore();}
    function tail(t,p) {
      c.save();c.translate(-36,42);c.rotate(p.tail);
      const fin=linear(-160,-100,-30,60,[[0,'#EEE0FA'],[.45,'#D1B9EE'],[1,'#A383CC']]);
      path(fin,()=>{c.moveTo(12,-3);c.bezierCurveTo(-58,6,-73,-71,-153,-95);c.bezierCurveTo(-184,-105,-193,-91,-204,-87);c.bezierCurveTo(-168,-75,-151,-53,-158,-21);c.bezierCurveTo(-181,23,-119,65,-56,43);c.bezierCurveTo(-20,36,3,31,12,18);c.closePath();});
      path(linear(-155,-80,-20,50,[[0,'#D3BDEE'],[.5,'#B99CDF'],[1,'#9270B9']]),()=>{c.moveTo(12,4);c.bezierCurveTo(-51,20,-95,15,-111,-23);c.bezierCurveTo(-124,-51,-152,-76,-189,-87);c.bezierCurveTo(-141,-75,-130,-36,-125,-6);c.bezierCurveTo(-120,35,-58,58,12,23);c.closePath();});
      line('rgba(255,255,255,.28)',1.8,()=>{c.moveTo(-175,-87);c.bezierCurveTo(-119,-62,-96,-10,-80,18);});
      line('rgba(255,255,255,.14)',1.2,()=>{c.moveTo(-176,-87);c.bezierCurveTo(-133,-70,-119,-50,-115,-25);});
      c.restore();
    }
    function foot(side,p) {
      c.save();c.translate(side*32,79);c.rotate(side*.055-p.lean*.4);
      oval(0,-2,24,28,linear(-17,-22,20,27,[[0,P.light],[.6,P.lilac],[1,P.shade]]));
      path(linear(-17,-6,13,30,[[0,'#CBB0EA'],[1,'#A584CD']]),()=>{c.moveTo(-23,8);c.bezierCurveTo(-27,24,-23,29,-10,30);c.bezierCurveTo(2,33,26,32,28,22);c.bezierCurveTo(30,10,18,5,9,3);c.bezierCurveTo(-7,-4,-18,-1,-23,8);});
      line('rgba(111,70,149,.23)',1.3,()=>{c.moveTo(-5,21);c.quadraticCurveTo(-6,25,-5,29);});
      line('rgba(111,70,149,.18)',1.3,()=>{c.moveTo(9,22);c.quadraticCurveTo(8,26,9,30);});c.restore();
    }
    function body(p,t) {
      c.save();c.scale(1.06+p.breath*.55,.98+p.breath);
      path(linear(-62,-58,64,85,[[0,'#DAC5F0'],[.45,'#BFA1E1'],[1,'#A07CC9']]),()=>{c.moveTo(0,-78);c.bezierCurveTo(51,-78,67,-27,71,23);c.bezierCurveTo(78,77,44,91,0,91);c.bezierCurveTo(-44,91,-78,77,-71,23);c.bezierCurveTo(-67,-27,-51,-78,0,-78);});
      path(linear(-25,-45,37,80,[[0,'#FFF6E6'],[.65,'#FAE5D1'],[1,'#E9CBBE']]),()=>{c.moveTo(0,-59);c.bezierCurveTo(33,-62,48,-15,49,30);c.bezierCurveTo(52,70,28,83,0,83);c.bezierCurveTo(-28,83,-52,70,-49,30);c.bezierCurveTo(-48,-15,-33,-62,0,-59);});
      glowOval(-15,-18,33,48,'rgba(255,255,255,.19)');c.restore();
    }
    function arm(side,angle) {
      c.save();c.translate(side*53,-29);c.scale(side,1);c.rotate(angle);
      path(linear(-17,10,23,74,[[0,'#D3B9EE'],[.5,'#BCA0E1'],[1,'#A780CB']]),()=>{c.moveTo(-15,-9);c.bezierCurveTo(-28,7,-21,37,-18,54);c.bezierCurveTo(-22,68,-13,82,-2,82);c.bezierCurveTo(6,84,14,79,17,71);c.bezierCurveTo(31,68,29,53,19,49);c.bezierCurveTo(20,29,22,8,12,-5);c.bezierCurveTo(5,-14,-8,-15,-15,-9);});
      glowOval(-7,60,13,17,'rgba(242,226,255,.27)');
      line('rgba(111,70,149,.17)',1.3,()=>{c.moveTo(-9,71);c.quadraticCurveTo(-8,75,-5,78);});
      line('rgba(111,70,149,.16)',1.3,()=>{c.moveTo(0,72);c.quadraticCurveTo(0,76,3,79);});c.restore();
    }
    function gill(side,i,t,p) {
      const y=[-35,3,40][i],angle=[-.70,-.02,.52][i],length=[55,69,54][i];
      c.save();c.translate(side*95,y);c.scale(side,1);c.rotate(angle+beat(t,2,.8+i*.4)*p.gills);
      path(linear(3,17,length,-15,[[0,'#DD807C'],[.32,P.peach],[1,P.peachLight]]),()=>{c.moveTo(-10,-12);c.bezierCurveTo(13,-13,length-19,-30,length-3,-17);c.bezierCurveTo(length+15,-3,length+6,18,length-12,19);c.bezierCurveTo(25,21,13,8,-10,13);c.closePath();});
      glowOval(length-12,-7,19,11,'rgba(255,236,213,.34)');c.restore();
    }
    function eye(x,y,side,p,blink) {
      // drowsy lowers a lid over the eye; only a deep yawn (drowsy > .75) closes it fully
      const joy=clamp(p.joy),closed=clamp(Math.max(blink,joy,(p.drowsy-.75)/.25)),lid=clamp(p.drowsy)*.55;
      const openness=1-closed;
      c.save();c.translate(x,y);c.scale(1,Math.max(.035,openness));
      c.globalAlpha=clamp(openness*6);
      oval(0,0,20,25,'#FFF8F5');
      c.save();c.beginPath();c.ellipse(0,0,20,25,0,0,Math.PI*2);c.clip();
      // cornea centred (the old side offset pushed it toward one edge of the white)
      const eyeX=p.gazeX,eyeY=p.gazeY+2;
      oval(eyeX,eyeY,15.7,22,linear(-3,-18,13,23,[[0,'#24152F'],[.5,'#41234B'],[1,'#75446E']]));
      oval(eyeX+1,eyeY-1,10,17,P.iris);
      oval(eyeX-5,eyeY-9,5.8,7,'rgba(255,255,255,.95)');
      oval(eyeX+7,eyeY+8,2.5,3,'rgba(255,236,245,.65)');
      if(lid>.01){c.fillStyle='#C6AAE6';c.fillRect(-22,-27,44,52*lid);line(P.plum,3.2,()=>{c.moveTo(-20,-25+52*lid);c.quadraticCurveTo(0,-23+52*lid,20,-25+52*lid);});}
      c.restore();
      c.restore();
      c.save();c.globalAlpha=clamp((closed-.45)/.5);line(P.plum,4.8,()=>{c.moveTo(x-13,y+2);c.quadraticCurveTo(x,y-(joy*8+2)+p.drowsy*7,x+13,y+2);});c.restore();
    }
    function mouth(p) {
      const v=clamp(p.mouth),w=14+v*7-p.round*3,h=2+v*26+p.yawn*16,openAlpha=clamp((v-.06)/.18);
      c.save();c.translate(0,43);
      c.globalAlpha=openAlpha;
      path(P.plum,()=>{c.moveTo(-w,0);c.quadraticCurveTo(0,10-v*10, w,0);c.bezierCurveTo(w+3,h*.65,w*.4,h+5,0,h+5);c.bezierCurveTo(-w*.4,h+5,-w-3,h*.65,-w,0);});
      c.save();c.clip();oval(0,h+7,13,7,P.peachLight);c.restore();
      // Blend a quiet closed smile into an open mouth without a hard shape switch.
      c.globalAlpha=1-openAlpha;
      line(P.plum,3.8,()=>{c.moveTo(-13,1);c.quadraticCurveTo(0,14,13,1);});c.restore();
    }
    function head(p,t) {
      const [hx,hy]=options.headScale||[1.0,.93];
      c.save();c.translate(-2,-144);c.rotate(p.head);c.scale(hx,hy);
      for(const side of [-1,1])for(let i=0;i<3;i++)gill(side,i,t,p);
      path(linear(-65,-86,80,91,[[0,'#E1CEF4'],[.32,'#CDB2EB'],[.75,'#B798DE'],[1,'#A886D1']]),()=>{c.moveTo(-2,-101);c.bezierCurveTo(71,-104,109,-59,114,9);c.bezierCurveTo(126,61,113,83,76,89);c.bezierCurveTo(29,99,-34,97,-79,86);c.bezierCurveTo(-118,77,-123,58,-113,9);c.bezierCurveTo(-108,-56,-73,-99,-2,-101);});
      glowOval(-34,-62,69,42,'rgba(255,255,255,.20)');
      glowOval(0,67,108,48,'rgba(255,234,219,.54)');
      glowOval(-73,45,27,20,'rgba(242,152,145,.46)');
      glowOval(73,45,27,20,'rgba(242,152,145,.46)');
      const blink=p.joy>.3?0:blinkAt(t);
      eye(-45,13,-1,p,blink);eye(45,13,1,p,blink);
      line('#8C669F',3.8,()=>{c.moveTo(-57,-26-p.brows*8);c.quadraticCurveTo(-47,-34-p.brows*7,-37,-28-p.brows*2);});
      line('#8C669F',3.8,()=>{c.moveTo(35,-28+p.brows*3);c.quadraticCurveTo(46,-34+p.brows*3,56,-26);});
      mouth(p);c.restore();
    }
    function star(x,y,r,a,rot=0) {c.save();c.translate(x,y);c.rotate(rot);c.globalAlpha=clamp(a);path(P.peach,()=>{c.moveTo(0,-r);c.quadraticCurveTo(r*.2,-r*.2,r,0);c.quadraticCurveTo(r*.2,r*.2,0,r);c.quadraticCurveTo(-r*.2,r*.2,-r,0);c.quadraticCurveTo(-r*.2,-r*.2,0,-r);});c.restore();}
    function render(t,state='ready',dt=1/60,immediate=false) {
      if(!STATES[state])state='ready';
      const target=pose(state,t),step=clamp(dt,0,.05),w=9;
      if(!current||immediate){current={...target};velocity=Object.fromEntries(Object.keys(target).map(k=>[k,0]));}
      else for(const k of Object.keys(target)){velocity[k]+=(w*w*(target[k]-current[k])-2*w*velocity[k])*step;current[k]+=velocity[k]*step;}
      const p=current;
      const sx=canvas.width/600,sy=canvas.height/500;c.setTransform(sx,0,0,sy,0,0);c.clearRect(0,0,600,500);
      if(options.background){c.fillStyle=options.background;c.fillRect(0,0,600,500);}
      c.save();c.translate(300,449);c.scale(1+p.lift*.005,.16);oval(0,0,106,106,radial(0,0,106,[[0,'rgba(67,36,87,.16)'],[.6,'rgba(67,36,87,.06)'],[1,'rgba(67,36,87,0)']]));c.restore();
      c.save();c.translate(300,340+p.lift);c.rotate(p.lean);
      tail(t,p);foot(-1,p);foot(1,p);body(p,t);arm(-1,p.left);
      // a hand at the chin must sit in front of the face, otherwise the head hides it
      if(p.think>.5){head(p,t);arm(1,p.right);}else{arm(1,p.right);head(p,t);}c.restore();
      if(p.listen>.005){c.save();c.globalAlpha=p.listen*(.45+.18*beat(t,2));line(P.peach,3.5,()=>{c.moveTo(112,173);c.quadraticCurveTo(100,186,112,199);});line(P.peach,3.5,()=>{c.moveTo(99,165);c.quadraticCurveTo(79,186,99,207);});c.restore();}
      if(p.speak>.005){c.save();c.globalAlpha=p.speak;for(let i=0;i<4;i++){const h=8+syllable(t-i*.07)*21;line(P.peach,4,()=>{c.moveTo(491+i*10,211-h/2);c.lineTo(491+i*10,211+h/2);});}c.restore();}
      if(p.think>.005){c.save();for(let i=0;i<3;i++){c.globalAlpha=p.think*(.25+.55*(beat(t,2,i*.75)*.5+.5));oval(414+i*16,99,3.5,3.5,P.lilac);}c.restore();}
      if(p.celebrate>.005){star(121,110,9+Math.sin(t*2)*2,p.celebrate*.8,t*.14);star(469,86,12+Math.sin(t*2+.7)*2,p.celebrate*.9,-t*.2);star(451,343,8+Math.sin(t*2+1.4)*2,p.celebrate*.7,t*.1);}
      return {...p};
    }
    return {render,states:STATES};
  }
  global.MimoFullBody={create,states:STATES};
  if(typeof module==='object'&&module.exports)module.exports=global.MimoFullBody;
})(typeof globalThis!=='undefined'?globalThis:window);
