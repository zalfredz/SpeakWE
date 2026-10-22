const fs=require('fs'),path=require('path');
const base=__dirname;
const engine=fs.readFileSync(path.join(base,'mimo-fullbody-engine.js'),'utf8');
const template=fs.readFileSync(path.join(base,'mimo-fullbody-template.html'),'utf8');
const html=template.replace('/* MIMO_ENGINE */',engine);
const outputs=[path.join(base,'Mimo-Full-Body-Demo.html'),path.join(process.env.USERPROFILE,'Downloads','SpeakWE-Mimo-Full-Body.html'),path.join(process.env.USERPROFILE,'Downloads','SpeakWE-Mimo-Demo.html')];
for(const out of outputs){fs.writeFileSync(out,html);console.log(out);}
