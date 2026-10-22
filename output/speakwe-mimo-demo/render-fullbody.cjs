const fs=require('fs'),path=require('path');
const {createCanvas}=require('./render-tools/node_modules/@napi-rs/canvas');
const Mimo=require('./mimo-fullbody-engine.js');
const base=__dirname,states=Object.keys(Mimo.states);
const sheet=createCanvas(1200,760),s=sheet.getContext('2d');s.fillStyle='#FAF7F1';s.fillRect(0,0,1200,760);
const samples={ready:1,listening:1.2,speaking:.7,thinking:1,encourage:1.6,success:1.2};
for(let i=0;i<states.length;i++){
 const state=states[i],tile=createCanvas(400,334),r=Mimo.create(tile,{background:'#FAF7F1'});r.render(samples[state],state,0,true);
 const x=(i%3)*400,y=Math.floor(i/3)*380;s.drawImage(tile,x,y);s.fillStyle='#422B4E';s.textAlign='center';s.font='19px sans-serif';s.fillText(Mimo.states[state][0],x+200,y+354);
}
fs.writeFileSync(path.join(base,'mimo-fullbody-contact.png'),sheet.toBuffer('image/png'));console.log('Rendered six-expression contact sheet');
if(process.argv.includes('--gif')){
 const {GIFEncoder,quantize,applyPalette}=require('./render-tools/node_modules/gifenc');
 const palette=quantize(s.getImageData(0,0,sheet.width,sheet.height).data,256);
 const canvas=createCanvas(420,350),ctx=canvas.getContext('2d'),r=Mimo.create(canvas,{background:'#FAF7F1'}),gif=GIFEncoder();
 const fps=30,seconds=18,frames=fps*seconds;
 for(let i=0;i<frames;i++){
  const state=states[Math.floor(i/(fps*3))%states.length];r.render(i/fps,state,1/fps,i===0);
  const pixels=ctx.getImageData(0,0,canvas.width,canvas.height).data,index=applyPalette(pixels,palette);
  gif.writeFrame(index,canvas.width,canvas.height,{palette,delay:i%3===0?40:30,repeat:0});
 }
 gif.finish();const file=path.join(process.env.USERPROFILE,'Downloads','SpeakWE-Mimo-Full-Body.gif');fs.writeFileSync(file,gif.bytes());console.log('GIF:',file,'Frames:',frames,'Bytes:',fs.statSync(file).size);
}
