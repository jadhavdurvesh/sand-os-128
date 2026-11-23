import createVeylithModule from "./veylith-vm.js";
export async function bootDisk(buffer,onOutput=()=>{}){
 const mod=await createVeylithModule({print:(s)=>onOutput(String(s)),printErr:(s)=>onOutput(String(s))});
 mod.FS.writeFile("/SAND-128.img",new Uint8Array(buffer));
 let code=0;try{code=mod.callMain(["/SAND-128.img"])??0;}catch(e){if(e?.name==="ExitStatus")code=e.status;else throw e;}
 const ptr=mod._veylith_framebuffer_ptr?.()||0;const size=mod._veylith_framebuffer_size?.()||0;const framebuffer=ptr&&size?new Uint8Array(mod.HEAPU8.buffer,ptr,size*4).slice():null;return {exitCode:code,module:mod,framebuffer};
}
