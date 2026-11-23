import createVeylithModule from "./veylith-vm.js";
export async function bootDisk(buffer,onOutput=()=>{}){
 const mod=await createVeylithModule({print:(s)=>onOutput(String(s)),printErr:(s)=>onOutput(String(s))});
 mod.FS.writeFile("/SAND-128.img",new Uint8Array(buffer));
 let code=0;try{code=mod.callMain(["/SAND-128.img"])??0;}catch(e){if(e?.name==="ExitStatus")code=e.status;else throw e;}
 const ptr=mod._veylith_framebuffer_ptr?.()||0;const size=mod._veylith_framebuffer_size?.()||0;const heap=mod.HEAPU8||(mod.wasmMemory?new Uint8Array(mod.wasmMemory.buffer):null);if(!heap)throw new Error("WebAssembly memory view was not exported by the Veylith module");const framebuffer=ptr&&size?Array.from(heap.subarray(ptr,ptr+size*4)):null;return {exitCode:code,framebuffer};
}
