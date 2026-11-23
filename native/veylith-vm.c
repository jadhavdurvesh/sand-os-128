/* SAND-128 Veylith 128-Native v1 hosted machine. GCC/Clang C11 with __int128. */
#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <inttypes.h>
typedef unsigned __int128 u128; typedef __int128 s128;
#define RAM_SIZE (1u<<20)
#define GLYPH 16
#define IMM_MASK ((((u128)1)<<88)-1)
#define CONSOLE_ADDR ((u128)-1-(u128)0xffff)
#define MAX_STEPS 5000000ULL
enum { ILLEGAL=1, PRIVILEGE=2, DIVZERO=3, MISALIGN=4, ACCESS=5, SYSCALL=6 };
enum { PRIV=0, TVEC=1, TPC=2, TCAUSE=3, TVAL=4, TPRIV=5, ABASE=6, ALIM=7, CYCLES=8, SCRATCH=9 };
typedef struct {u128 v[129],pc,csr[10];unsigned priv;unsigned char*ram;int halted,exit_code;uint64_t cycles;} Machine;
static const char*cause_name[]={"","ILLEGAL","PRIVILEGE","DIVZERO","MISALIGN","ACCESS","SYSCALL"};
static uint32_t le32(const unsigned char*p){return (uint32_t)p[0]|((uint32_t)p[1]<<8)|((uint32_t)p[2]<<16)|((uint32_t)p[3]<<24);}
static uint64_t le64(const unsigned char*p){uint64_t x=0;for(int i=7;i>=0;i--)x=(x<<8)|p[i];return x;}
static u128 le128(const unsigned char*p){u128 x=0;for(int i=15;i>=0;i--)x=(x<<8)|p[i];return x;}
static u128 sext(u128 x,unsigned n){u128 m=(((u128)1)<<n)-1;x&=m;return (x&(((u128)1)<<(n-1)))?(x|~m):x;}
static void fault(Machine*m,unsigned c,u128 val,u128 pc){if(!m->csr[TVEC]){fprintf(stderr,"\n[Machine] unhandled %s at PC 0x%016" PRIx64 "\n",cause_name[c],(uint64_t)pc);m->halted=1;m->exit_code=128+(int)c;return;}m->csr[TPC]=pc;m->csr[TCAUSE]=c;m->csr[TVAL]=val;m->csr[TPRIV]=m->priv;m->priv=0;m->pc=m->csr[TVEC];}
static int memcheck(Machine*m,u128 a,unsigned n,int wr){if(a%n)return MISALIGN;u128 end=a+n;if(end<a)return ACCESS;if(m->priv){if(a<m->csr[ABASE]||end>m->csr[ABASE]+m->csr[ALIM]||end>RAM_SIZE)return ACCESS;return 0;}if(end<=RAM_SIZE)return 0;if(wr&&a==CONSOLE_ADDR&&n==1)return 0;return ACCESS;}
static u128 loadn(Machine*m,u128 a,unsigned n,int*err){*err=memcheck(m,a,n,0);if(*err)return 0;u128 x=0;for(unsigned i=0;i<n;i++)x|=(u128)m->ram[(size_t)a+i]<<(8*i);return x;}
static int storen(Machine*m,u128 a,unsigned n,u128 x){int e=memcheck(m,a,n,1);if(e)return e;if(a==CONSOLE_ADDR&&n==1){putchar((unsigned char)x);fflush(stdout);return 0;}for(unsigned i=0;i<n;i++)m->ram[(size_t)a+i]=(unsigned char)(x>>(8*i));return 0;}
static u128 mulhi(u128 a,u128 b){u128 mask=((u128)1<<64)-1,a0=a&mask,a1=a>>64,b0=b&mask,b1=b>>64,p00=a0*b0,p01=a0*b1,p10=a1*b0,p11=a1*b1,mid=(p00>>64)+(uint64_t)p01+(uint64_t)p10;return p11+(p01>>64)+(p10>>64)+(mid>>64);}
static unsigned clz128(u128 x){if(!x)return 128;uint64_t hi=(uint64_t)(x>>64);return hi?(unsigned)__builtin_clzll(hi):64u+(unsigned)__builtin_clzll((uint64_t)x);}
static unsigned pop128(u128 x){return (unsigned)__builtin_popcountll((uint64_t)x)+(unsigned)__builtin_popcountll((uint64_t)(x>>64));}
static int valid(unsigned op,unsigned d,unsigned a,unsigned b,u128 im){int D=0,A=0,B=0,I=0;
switch(op){case 0:case 1:case 0x71:break;
case 0x10:case 0x11:case 0x12:case 0x13:case 0x14:case 0x15:case 0x16:case 0x17:case 0x18:case 0x19:case 0x1a:case 0x1b:case 0x1c:case 0x1d:case 0x1e:case 0x1f:case 0x28:case 0x29:case 0x2a:D=A=B=1;break;
case 0x20:case 0x21:case 0x22:case 0x23:case 0x24:case 0x25:case 0x26:D=A=I=1;break;
case 0x30:case 0x31:D=I=1;break;case 0x32:case 0x33:D=A=1;break;
case 0x40:case 0x41:case 0x42:case 0x43:case 0x44:case 0x45:case 0x46:case 0x47:case 0x48:D=A=I=1;break;
case 0x50:case 0x51:case 0x52:case 0x53:case 0x54:A=B=I=1;break;
case 0x60:case 0x70:I=1;break;case 0x61:D=I=1;break;case 0x62:D=A=I=1;break;
case 0x63:case 0x64:case 0x65:case 0x66:case 0x67:case 0x68:A=B=I=1;break;case 0x72:D=I=1;break;case 0x73:A=I=1;break;default:return 0;}
return (D||!d)&&(A||!a)&&(B||!b)&&(I||!im)&&d<=128&&a<=128&&b<=128;}
static void step(Machine*m){u128 pc=m->pc;if(pc>=RAM_SIZE||pc%16){fault(m,pc%16?MISALIGN:ACCESS,pc,pc);return;}u128 raw=le128(m->ram+(size_t)pc);unsigned op=(unsigned)(raw>>112),d=(unsigned)((raw>>104)&255),ai=(unsigned)((raw>>96)&255),bi=(unsigned)((raw>>88)&255);u128 im=raw&IMM_MASK;
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
case 0x40:case 0x41:case 0x42:case 0x43:case 0x44:case 0x45:case 0x46:case 0x47:case 0x48:{unsigned n=(op==0x40||op==0x45)?1:(op==0x41||op==0x46)?2:(op==0x42||op==0x47)?4:(op==0x43||op==0x48)?8:16;z=loadn(m,a+si,n,&e);if(e){fault(m,e,a+si,pc);return;}if(op>=0x45&&n<16)z=sext(z,n*8);wr=1;break;}
case 0x50:case 0x51:case 0x52:case 0x53:case 0x54:{unsigned n=op==0x50?1:op==0x51?2:op==0x52?4:op==0x53?8:16;e=storen(m,a+si,n,b);if(e){fault(m,e,a+si,pc);return;}break;}
case 0x60:npc=pc+16*(s128)si;break;case 0x61:npc=pc+16*(s128)si;if(d)m->v[d]=next;break;case 0x62:npc=a+si;if(d)m->v[d]=next;break;
case 0x63:br=a==b;goto BR;case 0x64:br=a!=b;goto BR;case 0x65:br=(s128)a<(s128)b;goto BR;case 0x66:br=(s128)a>=(s128)b;goto BR;case 0x67:br=a<b;goto BR;case 0x68:br=a>=b;BR:if(br)npc=pc+16*(s128)si;break;
case 0x70:fault(m,SYSCALL,im,next);return;case 0x71:if(m->priv){fault(m,PRIVILEGE,0,pc);return;}m->priv=(unsigned)(m->csr[TPRIV]&1);npc=m->csr[TPC];break;
case 0x72:if(m->priv){fault(m,PRIVILEGE,0,pc);return;}if(im==CYCLES)W(m->cycles);else if(im<10)W(m->csr[(unsigned)im]);else{fault(m,ILLEGAL,im,pc);return;}break;
case 0x73:if(m->priv){fault(m,PRIVILEGE,0,pc);return;}if(im>=10||im==PRIV||im==CYCLES){fault(m,ILLEGAL,im,pc);return;}m->csr[(unsigned)im]=a;break;default:fault(m,ILLEGAL,raw,pc);return;}
if(wr&&d)m->v[d]=z;m->v[0]=0;m->pc=npc;m->cycles++;
#undef W
}
static uint64_t hash64(const unsigned char*p,size_t n){uint64_t h=14695981039346656037ULL;for(size_t i=0;i<n;i++){h^=p[i];h*=1099511628211ULL;}return h;}
static int boot(const unsigned char*d,size_t size){if(size<512||memcmp(d,"SAND128D",8))return 2;if(le32(d+8)!=1||le32(d+12)!=512||le64(d+16)!=512)return 2;uint64_t len=le64(d+24);if(len>size-512||len<24)return 2;const unsigned char*p=d+512;if(hash64(p,(size_t)len)!=le64(d+32))return 2;if(memcmp(p,"VYLI",4)||le32(p+4)!=2)return 2;unsigned count=p[6]|(p[7]<<8);if(count>64)return 2;
Machine m;memset(&m,0,sizeof(m));m.ram=calloc(RAM_SIZE,1);if(!m.ram)return 2;size_t off=24;
for(unsigned i=0;i<count;i++){if(off+32>len){free(m.ram);return 2;}u128 addr=le128(p+off),sz=le128(p+off+16);off+=32;if(addr>RAM_SIZE||sz>RAM_SIZE-(size_t)addr||sz>len-off){free(m.ram);return 2;}memcpy(m.ram+(size_t)addr,p+off,(size_t)sz);off+=(size_t)sz;}
if(off!=len){free(m.ram);return 2;}m.pc=le128(p+8);fprintf(stderr,"[Veylith Firmware] SAND-128 disk verified\n[Veylith Bootloader] Kernelloom loaded; reset PC established\n");
while(!m.halted&&m.cycles<MAX_STEPS)step(&m);if(!m.halted){fprintf(stderr,"\n[Machine] step limit reached\n");free(m.ram);return 1;}fprintf(stderr,"\n[Machine] halted; exit code %d; %" PRIu64 " Glyphs retired\n",m.exit_code,m.cycles);free(m.ram);return m.exit_code==0?0:1;}
int main(int argc,char**argv){if(argc!=2){fprintf(stderr,"usage: veylith-vm <SAND-128.img>\n");return 2;}FILE*f=fopen(argv[1],"rb");if(!f){perror(argv[1]);return 2;}fseek(f,0,SEEK_END);long n=ftell(f);rewind(f);if(n<0){fclose(f);return 2;}unsigned char*b=malloc((size_t)n);if(!b){fclose(f);return 2;}if(fread(b,1,(size_t)n,f)!=(size_t)n){free(b);fclose(f);return 2;}fclose(f);int rc=boot(b,(size_t)n);free(b);if(rc==2)fprintf(stderr,"[Machine] invalid or incompatible SAND-128 disk image\n");return rc;}
