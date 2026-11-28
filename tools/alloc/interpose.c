/* LD_PRELOAD malloc logger: one binary record per event (op, ptr, size) appended to $ALLOC_TRACE. Used by tools/frag.py. */
#define _GNU_SOURCE
#include <dlfcn.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <fcntl.h>
static int fd = -2; static int busy = 0;
static void *(*real_malloc)(size_t); static void (*real_free)(void *); static void *(*real_calloc)(size_t, size_t); static void *(*real_realloc)(void *, size_t);
static char boot[1 << 16]; static size_t bootpos = 0;
static void init(void) {
    if (real_malloc) return;
    real_malloc = dlsym(RTLD_NEXT, "malloc"); real_free = dlsym(RTLD_NEXT, "free"); real_calloc = dlsym(RTLD_NEXT, "calloc"); real_realloc = dlsym(RTLD_NEXT, "realloc");
    const char *p = getenv("ALLOC_TRACE"); fd = p ? open(p, O_WRONLY | O_CREAT | O_APPEND, 0644) : -1;
}
static void rec(char op, void *ptr, size_t size) {
    if (fd < 0 || busy) return; busy = 1;
    struct { char op; uint64_t ptr, size; } __attribute__((packed)) r = {op, (uint64_t)(uintptr_t)ptr, (uint64_t)size};
    (void)!write(fd, &r, sizeof r); busy = 0;
}
void *malloc(size_t n) { if (!real_malloc) init(); void *p = real_malloc(n); rec('m', p, n); return p; }
void free(void *p) { if (!real_free) init(); if ((char *)p >= boot && (char *)p < boot + sizeof boot) return; rec('f', p, 0); real_free(p); }
void *calloc(size_t a, size_t b) {
    if (!real_calloc) { /* dlsym itself may call calloc */ if ((bootpos + a * b + 16) < sizeof boot) { void *p = boot + bootpos; bootpos += (a * b + 15) & ~15UL; return p; } return 0; }
    void *p = real_calloc(a, b); rec('m', p, a * b); return p;
}
void *realloc(void *p, size_t n) { if (!real_realloc) init(); void *q = real_realloc(p, n); rec('f', p, 0); rec('m', q, n); return q; }
