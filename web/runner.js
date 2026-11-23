import createVeylithModule from "./veylith-vm.js";
export async function bootDisk(buffer,onOutput=()=>{}){
 const mod=await createVeylithModule({print:(s)=>onOutput(String(s)),printErr:(s)=>onOutput(String(s))});
 mod.FS.writeFile("/SAND-128.img",new Uint8Array(buffer));
 const code=mod.callMain(["/SAND-128.img"]);
 return {exitCode:code,module:mod};
}
