import createVeylithModule from "./veylith-vm.js";
export async function bootDisk(buffer,onOutput=()=>{}){
 const mod=await createVeylithModule({print:(s)=>onOutput(String(s)),printErr:(s)=>onOutput(String(s))});
 mod.FS.writeFile("/SAND-128.img",new Uint8Array(buffer));
 let code=0;try{code=mod.callMain(["/SAND-128.img"])??0;}catch(e){if(e?.name==="ExitStatus")code=e.status;else throw e;}
 return {exitCode:code,module:mod};
}
