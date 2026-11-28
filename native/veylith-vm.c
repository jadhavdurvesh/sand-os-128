/* SAND-128 Veylith 128-Native v1 hosted machine. GCC/Clang C11 with __int128. */
#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <inttypes.h>
#include <ctype.h>
typedef unsigned __int128 u128; typedef __int128 s128;
#define RAM_SIZE (1u<<20)
#define GLYPH 16
#define IMM_MASK ((((u128)1)<<88)-1)
#define CONSOLE_ADDR ((u128)-1-(u128)0xffff)
#define MAX_STEPS 5000000ULL
enum { ILLEGAL=1, PRIVILEGE=2, DIVZERO=3, MISALIGN=4, ACCESS=5, SYSCALL=6, TIMER=7, CAPABILITY=8 };
enum { PRIV=0, TVEC=1, TPC=2, TCAUSE=3, TVAL=4, TPRIV=5, ABASE=6, ALIM=7, CYCLES=8, SCRATCH=9, TIMECMP=10, CKEY=11, CMODE=12, CLINK=13, CSTACK=14 };
typedef struct {u128 v[129],pc,csr[15];unsigned priv;unsigned char*ram;int halted,exit_code;uint64_t cycles;} Machine;
#define GPU_BASE ((u128)-1-(u128)0x1fff)
#define GPU_WIDTH 1280u
#define GPU_HEIGHT 720u
#define GPU_PIXELS (GPU_WIDTH*GPU_HEIGHT)
static uint32_t *veylith_fb;
static u128 gpu_regs[6];
uint32_t *veylith_framebuffer_ptr(void){return veylith_fb;}
uint32_t veylith_framebuffer_size(void){return GPU_PIXELS;}
static const char*cause_name[]={"","ILLEGAL","PRIVILEGE","DIVZERO","MISALIGN","ACCESS","SYSCALL","TIMER","CAPABILITY"};
static uint32_t le32(const unsigned char*p){return (uint32_t)p[0]|((uint32_t)p[1]<<8)|((uint32_t)p[2]<<16)|((uint32_t)p[3]<<24);}
static uint64_t le64(const unsigned char*p){uint64_t x=0;for(int i=7;i>=0;i--)x=(x<<8)|p[i];return x;}
static u128 le128(const unsigned char*p){u128 x=0;for(int i=15;i>=0;i--)x=(x<<8)|p[i];return x;}
static u128 sext(u128 x,unsigned n){u128 m=(((u128)1)<<n)-1;x&=m;return (x&(((u128)1)<<(n-1)))?(x|~m):x;}
static void fault(Machine*m,unsigned c,u128 val,u128 pc){if(!m->csr[TVEC]){fprintf(stderr,"\n[Machine] unhandled %s at PC 0x%016" PRIx64 "\n",cause_name[c],(uint64_t)pc);m->halted=1;m->exit_code=128+(int)c;return;}m->csr[TPC]=pc;m->csr[TCAUSE]=c;m->csr[TVAL]=val;m->csr[TPRIV]=m->priv;m->priv=0;m->pc=m->csr[TVEC];}
static int memcheck(Machine*m,u128 a,unsigned n,int wr){if(a>=GPU_BASE&&a<GPU_BASE+96){if(m->priv||!wr||n!=16||((a-GPU_BASE)%16))return ACCESS;return 0;}if(a%n)return MISALIGN;u128 end=a+n;if(end<a)return ACCESS;if(m->priv){if(a<m->csr[ABASE]||end>m->csr[ABASE]+m->csr[ALIM]||end>RAM_SIZE)return ACCESS;return 0;}if(end<=RAM_SIZE)return 0;if(wr&&a==CONSOLE_ADDR&&n==1)return 0;return ACCESS;}
static u128 loadn(Machine*m,u128 a,unsigned n,int*err){*err=memcheck(m,a,n,0);if(*err)return 0;u128 x=0;for(unsigned i=0;i<n;i++)x|=(u128)m->ram[(size_t)a+i]<<(8*i);return x;}

static void glyph5x7(unsigned char ch,uint8_t out[7]){
 memset(out,0,7);ch=(unsigned char)toupper(ch);
 switch(ch){case '0':{static const uint8_t g[7]={14,17,19,21,25,17,14};memcpy(out,g,7);return;}case '1':{static const uint8_t g[7]={4,12,4,4,4,4,14};memcpy(out,g,7);return;}case '2':{static const uint8_t g[7]={14,17,1,2,4,8,31};memcpy(out,g,7);return;}case '3':{static const uint8_t g[7]={30,1,1,14,1,1,30};memcpy(out,g,7);return;}case '4':{static const uint8_t g[7]={2,6,10,18,31,2,2};memcpy(out,g,7);return;}case '5':{static const uint8_t g[7]={31,16,16,30,1,1,30};memcpy(out,g,7);return;}case '6':{static const uint8_t g[7]={14,16,16,30,17,17,14};memcpy(out,g,7);return;}case '7':{static const uint8_t g[7]={31,1,2,4,8,8,8};memcpy(out,g,7);return;}case '8':{static const uint8_t g[7]={14,17,17,14,17,17,14};memcpy(out,g,7);return;}case '9':{static const uint8_t g[7]={14,17,17,15,1,1,14};memcpy(out,g,7);return;}case 'A':{static const uint8_t g[7]={14,17,17,31,17,17,17};memcpy(out,g,7);return;}case 'B':{static const uint8_t g[7]={30,17,17,30,17,17,30};memcpy(out,g,7);return;}case 'C':{static const uint8_t g[7]={14,17,16,16,16,17,14};memcpy(out,g,7);return;}case 'D':{static const uint8_t g[7]={30,17,17,17,17,17,30};memcpy(out,g,7);return;}case 'E':{static const uint8_t g[7]={31,16,16,30,16,16,31};memcpy(out,g,7);return;}case 'F':{static const uint8_t g[7]={31,16,16,30,16,16,16};memcpy(out,g,7);return;}case 'G':{static const uint8_t g[7]={14,17,16,23,17,17,15};memcpy(out,g,7);return;}case 'H':{static const uint8_t g[7]={17,17,17,31,17,17,17};memcpy(out,g,7);return;}case 'I':{static const uint8_t g[7]={14,4,4,4,4,4,14};memcpy(out,g,7);return;}case 'J':{static const uint8_t g[7]={7,2,2,2,18,18,12};memcpy(out,g,7);return;}case 'K':{static const uint8_t g[7]={17,18,20,24,20,18,17};memcpy(out,g,7);return;}case 'L':{static const uint8_t g[7]={16,16,16,16,16,16,31};memcpy(out,g,7);return;}case 'M':{static const uint8_t g[7]={17,27,21,21,17,17,17};memcpy(out,g,7);return;}case 'N':{static const uint8_t g[7]={17,25,21,19,17,17,17};memcpy(out,g,7);return;}case 'O':{static const uint8_t g[7]={14,17,17,17,17,17,14};memcpy(out,g,7);return;}case 'P':{static const uint8_t g[7]={30,17,17,30,16,16,16};memcpy(out,g,7);return;}case 'Q':{static const uint8_t g[7]={14,17,17,17,21,18,13};memcpy(out,g,7);return;}case 'R':{static const uint8_t g[7]={30,17,17,30,20,18,17};memcpy(out,g,7);return;}case 'S':{static const uint8_t g[7]={15,16,16,14,1,1,30};memcpy(out,g,7);return;}case 'T':{static const uint8_t g[7]={31,4,4,4,4,4,4};memcpy(out,g,7);return;}case 'U':{static const uint8_t g[7]={17,17,17,17,17,17,14};memcpy(out,g,7);return;}case 'V':{static const uint8_t g[7]={17,17,17,17,17,10,4};memcpy(out,g,7);return;}case 'W':{static const uint8_t g[7]={17,17,17,21,21,21,10};memcpy(out,g,7);return;}case 'X':{static const uint8_t g[7]={17,17,10,4,10,17,17};memcpy(out,g,7);return;}case 'Y':{static const uint8_t g[7]={17,17,10,4,4,4,4};memcpy(out,g,7);return;}case 'Z':{static const uint8_t g[7]={31,1,2,4,8,16,31};memcpy(out,g,7);return;}case '.':{static const uint8_t g[7]={0,0,0,0,0,12,12};memcpy(out,g,7);return;}case ':':{static const uint8_t g[7]={0,12,12,0,12,12,0};memcpy(out,g,7);return;}case '-':{static const uint8_t g[7]={0,0,0,31,0,0,0};memcpy(out,g,7);return;}case '/':{static const uint8_t g[7]={1,2,2,4,8,8,16};memcpy(out,g,7);return;}default:break;}
}
static void gpu_text(Machine*m,uint64_t x,uint64_t y,uint64_t ptr,uint64_t len,uint32_t color){
 if(ptr>=RAM_SIZE||len>128||len>RAM_SIZE-ptr)return;
 for(uint64_t i=0;i<len;i++){uint8_t rows[7];glyph5x7(m->ram[ptr+i],rows);
  for(unsigned ry=0;ry<7;ry++)for(unsigned rx=0;rx<5;rx++)if(rows[ry]&(1u<<(4-rx)))
   for(unsigned sy=0;sy<2;sy++)for(unsigned sx=0;sx<2;sx++){uint64_t px=x+i*12+rx*2+sx,py=y+ry*2+sy;if(px<GPU_WIDTH&&py<GPU_HEIGHT)veylith_fb[py*GPU_WIDTH+px]=color;}
 }
}

static void gpu_write(Machine*m,u128 a,u128 x){unsigned r=(unsigned)((a-GPU_BASE)/16);if(r<5){gpu_regs[r]=x;return;}gpu_regs[5]=x;if(!veylith_fb)return;if(x==2){gpu_text(m,(uint64_t)gpu_regs[0],(uint64_t)gpu_regs[1],(uint64_t)gpu_regs[2],(uint64_t)gpu_regs[3],(uint32_t)gpu_regs[4]);return;}if(x!=1)return;uint64_t px=(uint64_t)gpu_regs[0],py=(uint64_t)gpu_regs[1],w=(uint64_t)gpu_regs[2],h=(uint64_t)gpu_regs[3];uint32_t color=(uint32_t)gpu_regs[4];if(px>=GPU_WIDTH||py>=GPU_HEIGHT)return;if(w>GPU_WIDTH-px)w=GPU_WIDTH-px;if(h>GPU_HEIGHT-py)h=GPU_HEIGHT-py;for(uint64_t yy=py;yy<py+h;yy++)for(uint64_t xx=px;xx<px+w;xx++)veylith_fb[yy*GPU_WIDTH+xx]=color;}
static int storen(Machine*m,u128 a,unsigned n,u128 x){int e=memcheck(m,a,n,1);if(e)return e;if(a>=GPU_BASE&&a<GPU_BASE+96){gpu_write(m,a,x);return 0;}if(a==CONSOLE_ADDR&&n==1){putchar((unsigned char)x);fflush(stdout);return 0;}for(unsigned i=0;i<n;i++)m->ram[(size_t)a+i]=(unsigned char)(x>>(8*i));return 0;}
static u128 mulhi(u128 a,u128 b){u128 mask=((u128)1<<64)-1,a0=a&mask,a1=a>>64,b0=b&mask,b1=b>>64,p00=a0*b0,p01=a0*b1,p10=a1*b0,p11=a1*b1,mid=(p00>>64)+(uint64_t)p01+(uint64_t)p10;return p11+(p01>>64)+(p10>>64)+(mid>>64);}
static unsigned clz128(u128 x){if(!x)return 128;uint64_t hi=(uint64_t)(x>>64);return hi?(unsigned)__builtin_clzll(hi):64u+(unsigned)__builtin_clzll((uint64_t)x);}
static unsigned pop128(u128 x){return (unsigned)__builtin_popcountll((uint64_t)x)+(unsigned)__builtin_popcountll((uint64_t)(x>>64));}
/* Sigil capabilities: [127:88] MAC | [87:80] perms | [79:72] exp | [71:0] base (see docs/18) */
static const u128 SIGIL_K=(((u128)0x9E3779B97F4A7C15ULL)<<64)|(u128)0xF39CC0605CEDC835ULL;
#define SIGIL_BODY ((((u128)1)<<88)-1)
static uint64_t rotl64(uint64_t x,unsigned b){return (x<<b)|(x>>(64-b));}
#define SIPR do{v0+=v1;v1=rotl64(v1,13);v1^=v0;v0=rotl64(v0,32);v2+=v3;v3=rotl64(v3,16);v3^=v2;v0+=v3;v3=rotl64(v3,21);v3^=v0;v2+=v1;v1=rotl64(v1,17);v1^=v2;v2=rotl64(v2,32);}while(0)
/* SipHash-2-4, 128-bit key; message is the 88-bit body as 11 little-endian bytes. */
static u128 sigil_mac(u128 key,u128 body){uint64_t k0=(uint64_t)key,k1=(uint64_t)(key>>64);uint64_t v0=k0^0x736F6D6570736575ULL,v1=k1^0x646F72616E646F6DULL,v2=k0^0x6C7967656E657261ULL,v3=k1^0x7465646279746573ULL;uint64_t m=(uint64_t)body;v3^=m;SIPR;SIPR;v0^=m;m=((uint64_t)11<<56)|(uint64_t)(body>>64);v3^=m;SIPR;SIPR;v0^=m;v2^=0xFF;SIPR;SIPR;SIPR;SIPR;return (u128)((v0^v1^v2^v3)>>24);}
static u128 sigil_size(unsigned shape){return ((u128)((shape&255)+1))<<(shape>>8);}
static u128 sigil_make(u128 key,u128 base,unsigned perms,unsigned shape){u128 body=((u128)perms<<80)|((u128)shape<<64)|base;return (sigil_mac(key,body)<<88)|body;}
static int sigil_parse(u128 key,u128 cap,u128*base,unsigned*perms,unsigned*exp){u128 body=cap&SIGIL_BODY;if((cap>>88)!=sigil_mac(key,body))return 0;unsigned p=(unsigned)((cap>>80)&255),sh=(unsigned)((cap>>64)&0xFFFF),e=sh>>8;u128 b=(uint64_t)cap;if((p&~0x8Fu)||e>56||(b&((((u128)1)<<e)-1))||b+sigil_size(sh)>(((u128)1)<<64))return 0;*base=b;*perms=p;*exp=sh;return 1;}
static int valid(unsigned op,unsigned d,unsigned a,unsigned b,u128 im){int D=0,A=0,B=0,I=0;
switch(op){case 0:case 1:case 0x71:case 0x8A:case 0x8C:break;
case 0x10:case 0x11:case 0x12:case 0x13:case 0x14:case 0x15:case 0x16:case 0x17:case 0x18:case 0x19:case 0x1a:case 0x1b:case 0x1c:case 0x1d:case 0x1e:case 0x1f:case 0x28:case 0x29:case 0x2a:D=A=B=1;break;
case 0x20:case 0x21:case 0x22:case 0x23:case 0x24:case 0x25:case 0x26:D=A=I=1;break;
case 0x30:case 0x31:D=I=1;break;case 0x32:case 0x33:D=A=1;break;
case 0x40:case 0x41:case 0x42:case 0x43:case 0x44:case 0x45:case 0x46:case 0x47:case 0x48:D=A=I=1;break;
case 0x50:case 0x51:case 0x52:case 0x53:case 0x54:A=B=I=1;break;
case 0x60:case 0x70:I=1;break;case 0x61:D=I=1;break;case 0x62:D=A=I=1;break;
case 0x80:case 0x81:D=A=B=1;break;case 0x82:case 0x87:case 0x88:case 0x89:case 0x8B:D=A=1;break;case 0x83:case 0x84:D=A=I=1;break;case 0x85:case 0x86:A=B=I=1;break;
case 0x63:case 0x64:case 0x65:case 0x66:case 0x67:case 0x68:A=B=I=1;break;case 0x72:D=I=1;break;case 0x73:A=I=1;break;default:return 0;}
return (D||!d)&&(A||!a)&&(B||!b)&&(I||!im)&&d<=128&&a<=128&&b<=128;}
static void step(Machine*m){u128 pc=m->pc;if(m->priv==1&&m->csr[TIMECMP]&&m->csr[TVEC]&&(u128)m->cycles>=m->csr[TIMECMP]){m->csr[TIMECMP]=0;fault(m,TIMER,0,pc);return;}if(pc>=RAM_SIZE||pc%16){fault(m,pc%16?MISALIGN:ACCESS,pc,pc);return;}u128 raw=le128(m->ram+(size_t)pc);unsigned op=(unsigned)(raw>>112),d=(unsigned)((raw>>104)&255),ai=(unsigned)((raw>>96)&255),bi=(unsigned)((raw>>88)&255);u128 im=raw&IMM_MASK;
if(!valid(op,d,ai,bi,im)){fault(m,ILLEGAL,raw,pc);return;}u128 a=m->v[ai],b=m->v[bi],si=sext(im,88),next=pc+16,npc=next,z=0;int wr=0,e=0,br=0;
#define W(x) do{z=(u128)(x);wr=1;}while(0)
switch(op){case 0:break;case 1:if(m->priv){fault(m,PRIVILEGE,0,pc);return;}m->halted=1;m->exit_code=(int)m->v[1];break;
case 0x10:W(a+b);break;case 0x11:W(a-b);break;case 0x12:W(a*b);break;case 0x13:W(mulhi(a,b));break;
case 0x14:case 0x16:if(!b){fault(m,DIVZERO,0,pc);return;}W(op==0x14?a/b:a%b);break;
case 0x15:case 0x17:if(!b){fault(m,DIVZERO,0,pc);return;}{s128 x=(s128)a,y=(s128)b;if(x==((s128)((u128)1<<127))&&y==-1)W(op==0x15?(u128)x:0);else W(op==0x15?(u128)(x/y):(u128)(x%y));}break;
case 0x18:W(a&b);break;case 0x19:W(a|b);break;case 0x1a:W(a^b);break;case 0x1b:W(a<<(unsigned)(b%128));break;case 0x1c:W(a>>(unsigned)(b%128));break;case 0x1d:W((u128)((s128)a>>(unsigned)(b%128)));break;
case 0x1e:{unsigned n=(unsigned)(b%128);W(n?((a<<n)|(a>>(128-n))):a);break;}case 0x1f:{unsigned n=(unsigned)(b%128);W(n?((a>>n)|(a<<(128-n))):a);break;}
case 0x20:W(a+si);break;case 0x21:W(a&si);break;case 0x22:W(a|si);break;case 0x23:W(a^si);break;case 0x24:W(a<<(unsigned)(im%128));break;case 0x25:W(a>>(unsigned)(im%128));break;case 0x26:W((u128)((s128)a>>(unsigned)(im%128)));break;
case 0x28:W((s128)a<(s128)b);break;case 0x29:W(a<b);break;case 0x2a:W(a==b);break;case 0x30:W(si);break;case 0x31:W(((m->v[d]&((((u128)1)<<40)-1))<<88)|im);break;case 0x32:W(clz128(a));break;case 0x33:W(pop128(a));break;
case 0x40:case 0x41:case 0x42:case 0x43:case 0x44:case 0x45:case 0x46:case 0x47:case 0x48:{if(m->priv==1&&m->csr[CMODE]){fault(m,CAPABILITY,a+si,pc);return;}unsigned n=(op==0x40||op==0x45)?1:(op==0x41||op==0x46)?2:(op==0x42||op==0x47)?4:(op==0x43||op==0x48)?8:16;z=loadn(m,a+si,n,&e);if(e){fault(m,e,a+si,pc);return;}if(op>=0x45&&n<16)z=sext(z,n*8);wr=1;break;}
case 0x50:case 0x51:case 0x52:case 0x53:case 0x54:{if(m->priv==1&&m->csr[CMODE]){fault(m,CAPABILITY,a+si,pc);return;}unsigned n=op==0x50?1:op==0x51?2:op==0x52?4:op==0x53?8:16;e=storen(m,a+si,n,b);if(e){fault(m,e,a+si,pc);return;}break;}
case 0x60:npc=pc+16*(s128)si;break;case 0x61:npc=pc+16*(s128)si;if(d)m->v[d]=next;break;case 0x62:npc=a+si;if(d)m->v[d]=next;break;
case 0x63:br=a==b;goto BR;case 0x64:br=a!=b;goto BR;case 0x65:br=(s128)a<(s128)b;goto BR;case 0x66:br=(s128)a>=(s128)b;goto BR;case 0x67:br=a<b;goto BR;case 0x68:br=a>=b;BR:if(br)npc=pc+16*(s128)si;break;
case 0x80:{if(m->priv){fault(m,PRIVILEGE,0,pc);return;}unsigned pe=(unsigned)(b&255),ex=(unsigned)((((b>>8)&255)<<8)|((b>>16)&255));if((b>>24)||(pe&~0x8Fu)||(ex>>8)>56||(a>>64)||(a&((((u128)1)<<(ex>>8))-1))||a+sigil_size(ex)>(((u128)1)<<64)){fault(m,CAPABILITY,a,pc);return;}W(sigil_make(m->csr[CKEY],a,pe,ex));break;}
case 0x81:{u128 base;unsigned pe,ex;if(!sigil_parse(m->csr[CKEY],a,&base,&pe,&ex)){fault(m,CAPABILITY,a,pc);return;}unsigned np=(unsigned)(b&255),ne=(unsigned)((b>>8)&255);u128 off=(uint64_t)(b>>16);unsigned nsh=(ne<<8)|(unsigned)((b>>80)&255);if((b>>88)||(pe&0x80)||(np&~pe)||!(pe&4)||ne>(ex>>8)||(off&((((u128)1)<<ne)-1))||off+sigil_size(nsh)>sigil_size(ex)){fault(m,CAPABILITY,a,pc);return;}W(sigil_make(m->csr[CKEY],base+off,np,nsh));break;}
case 0x82:{u128 base;unsigned pe,ex;W(sigil_parse(m->csr[CKEY],a,&base,&pe,&ex)?((((u128)1)<<127)|(a&SIGIL_BODY)):0);break;}
case 0x87:{u128 base;unsigned pe,ex;if(!sigil_parse(m->csr[CKEY],a,&base,&pe,&ex)){fault(m,CAPABILITY,a,pc);return;}W(sigil_make(m->csr[CKEY],base,pe|0x80,ex));break;}
case 0x8B:{u128 base;unsigned pe,ex;u128 cs=m->csr[CSTACK];if(!sigil_parse(m->csr[CKEY],a,&base,&pe,&ex)||(pe&0x88)!=0x88||(base&15)||sigil_size(ex)<16||m->csr[CLINK]||cs==0||(cs&15)||cs+2048>RAM_SIZE){fault(m,CAPABILITY,a,pc);return;}u128 data=sigil_make(m->csr[CKEY],base,pe&~0x88u,ex);for(unsigned i=1;i<129;i++){u128 x=m->v[i];for(unsigned j=0;j<16;j++)m->ram[(size_t)cs+16*(i-1)+j]=(unsigned char)(x>>(8*j));if(i>4)m->v[i]=0;}W(data);m->csr[CLINK]=next|(((u128)1)<<127);npc=base;break;}
case 0x8C:{u128 cs=m->csr[CSTACK];if(!(m->csr[CLINK]>>127)){fault(m,CAPABILITY,0,pc);return;}for(unsigned i=3;i<129;i++){u128 x=0;for(unsigned j=0;j<16;j++)x|=(u128)m->ram[(size_t)cs+16*(i-1)+j]<<(8*j);m->v[i]=x;}npc=m->csr[CLINK]&((((u128)1)<<127)-1);m->csr[CLINK]=0;break;}
case 0x89:{u128 base;unsigned pe,ex;if(!sigil_parse(m->csr[CKEY],a,&base,&pe,&ex)||(pe&0x88)!=0x88||(base&15)||sigil_size(ex)<16||m->csr[CLINK]){fault(m,CAPABILITY,a,pc);return;}W(sigil_make(m->csr[CKEY],base,pe&~0x88u,ex));m->csr[CLINK]=next;npc=base;break;}
case 0x8A:{if(!m->csr[CLINK]||(m->csr[CLINK]>>127)){fault(m,CAPABILITY,0,pc);return;}npc=m->csr[CLINK];m->csr[CLINK]=0;break;}
case 0x88:{if(m->priv){fault(m,PRIVILEGE,0,pc);return;}u128 base;unsigned pe,ex;if(!sigil_parse(m->csr[CKEY],a,&base,&pe,&ex)||!(pe&0x80)){fault(m,CAPABILITY,a,pc);return;}W(sigil_make(m->csr[CKEY],base,pe&~0x80u,ex));break;}
case 0x83:case 0x84:case 0x85:case 0x86:{u128 base;unsigned pe,ex;unsigned n=(op==0x83||op==0x85)?1:16;int ld=op<=0x84;s128 off=(s128)si;if(!sigil_parse(m->csr[CKEY],a,&base,&pe,&ex)||(pe&0x80)||!(pe&(ld?1u:2u))||off<0||(u128)off+n>sigil_size(ex)){fault(m,CAPABILITY,a,pc);return;}
 if(ld){z=loadn(m,base+(u128)off,n,&e);if(e){fault(m,e,base+(u128)off,pc);return;}wr=1;}else{e=storen(m,base+(u128)off,n,b);if(e){fault(m,e,base+(u128)off,pc);return;}}break;}
case 0x70:fault(m,SYSCALL,im,next);return;case 0x71:if(m->priv){fault(m,PRIVILEGE,0,pc);return;}m->priv=(unsigned)(m->csr[TPRIV]&1);npc=m->csr[TPC];break;
case 0x72:if(m->priv){fault(m,PRIVILEGE,0,pc);return;}if(im==CYCLES)W(m->cycles);else if(im<15)W(m->csr[(unsigned)im]);else{fault(m,ILLEGAL,im,pc);return;}break;
case 0x73:if(m->priv){fault(m,PRIVILEGE,0,pc);return;}if(im>=15||im==PRIV||im==CYCLES){fault(m,ILLEGAL,im,pc);return;}m->csr[(unsigned)im]=a;break;default:fault(m,ILLEGAL,raw,pc);return;}
if(wr&&d)m->v[d]=z;m->v[0]=0;m->pc=npc;m->cycles++;
#undef W
}
static uint64_t hash64(const unsigned char*p,size_t n){uint64_t h=14695981039346656037ULL;for(size_t i=0;i<n;i++){h^=p[i];h*=1099511628211ULL;}return h;}
static int boot(const unsigned char*d,size_t size){if(size<512||memcmp(d,"SAND128D",8))return 2;if(le32(d+8)!=1||le32(d+12)!=512||le64(d+16)!=512)return 2;uint64_t len=le64(d+24);if(len>size-512||len<24)return 2;const unsigned char*p=d+512;if(hash64(p,(size_t)len)!=le64(d+32))return 2;if(memcmp(p,"VYLI",4)||p[4]!=2||p[5]!=0)return 2;unsigned count=p[6]|(p[7]<<8);if(count>64)return 2;
Machine m;memset(&m,0,sizeof(m));m.ram=calloc(RAM_SIZE,1);if(!m.ram)return 2;if(!veylith_fb)veylith_fb=calloc(GPU_PIXELS,sizeof(uint32_t));if(!veylith_fb){free(m.ram);return 2;}memset(veylith_fb,0,GPU_PIXELS*sizeof(uint32_t));memset(gpu_regs,0,sizeof(gpu_regs));size_t off=24;
for(unsigned i=0;i<count;i++){if(off+32>len){free(m.ram);return 2;}u128 addr=le128(p+off),sz=le128(p+off+16);off+=32;if(addr>RAM_SIZE||sz>RAM_SIZE-(size_t)addr||sz>len-off){free(m.ram);return 2;}memcpy(m.ram+(size_t)addr,p+off,(size_t)sz);off+=(size_t)sz;}
if(off!=len){free(m.ram);return 2;}m.pc=le128(p+8);fprintf(stderr,"[Veylith Firmware] SAND-128 disk verified\n[Veylith Bootloader] Kernelloom loaded; reset PC established\n");
while(!m.halted&&m.cycles<MAX_STEPS)step(&m);if(!m.halted){fprintf(stderr,"\n[Machine] step limit reached\n");free(m.ram);return 1;}fprintf(stderr,"\n[Machine] halted; exit code %d; %" PRIu64 " Glyphs retired\n",m.exit_code,m.cycles);free(m.ram);return m.exit_code==0?0:1;}
int main(int argc,char**argv){if(argc!=2){fprintf(stderr,"usage: veylith-vm <SAND-128.img>\n");return 2;}FILE*f=fopen(argv[1],"rb");if(!f){perror(argv[1]);return 2;}fseek(f,0,SEEK_END);long n=ftell(f);rewind(f);if(n<0){fclose(f);return 2;}unsigned char*b=malloc((size_t)n);if(!b){fclose(f);return 2;}if(fread(b,1,(size_t)n,f)!=(size_t)n){free(b);fclose(f);return 2;}fclose(f);int rc=boot(b,(size_t)n);free(b);if(rc==2)fprintf(stderr,"[Machine] invalid or incompatible SAND-128 disk image\n");return rc;}
