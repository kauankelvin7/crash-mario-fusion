/* CMW1 read-only observer. Independent of the CMJ1 channel and configuration. */
#ifndef _WIN32
#define _POSIX_C_SOURCE 200809L
#endif
#include "cm64_pose.h"
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <time.h>
#ifdef _WIN32
#include <winsock2.h>
#include <windows.h>
typedef SOCKET pose_socket;
#define INVALID_POSE_SOCKET INVALID_SOCKET
#define CLOSE_POSE closesocket
#else
#include <sys/socket.h>
#include <netinet/in.h>
#include <fcntl.h>
#include <unistd.h>
typedef int pose_socket;
#define INVALID_POSE_SOCKET (-1)
#define CLOSE_POSE close
#endif
_Static_assert(sizeof(float) == 4, "CMW1 requires binary32");
static pose_socket channel = INVALID_POSE_SOCKET;
static struct sockaddr_in destination;
static unsigned char session[16];
static int initialized, active, exhausted;
static int16_t last_level, last_area;
static uint32_t sequence, generation;
static uint64_t last_ms, start_ms;
static int sent;
static void be16(unsigned char *p, uint16_t v) { p[0]=(unsigned char)(v>>8); p[1]=(unsigned char)v; }
static void be32(unsigned char *p, uint32_t v) {
    p[0]=(unsigned char)(v>>24); p[1]=(unsigned char)(v>>16);
    p[2]=(unsigned char)(v>>8); p[3]=(unsigned char)v;
}
static uint64_t monotonic_ms(void) {
#ifdef CM64_POSE_TEST_CLOCK
    extern uint64_t cm64_pose_test_ms;
    return cm64_pose_test_ms;
#elif defined(_WIN32)
    return GetTickCount64();
#else
    struct timespec ts;
    if (clock_gettime(CLOCK_MONOTONIC, &ts)) return 0;
    return (uint64_t)ts.tv_sec*1000+(uint64_t)ts.tv_nsec/1000000;
#endif
}
static void shutdown_pose(void) {
    if (channel != INVALID_POSE_SOCKET) { CLOSE_POSE(channel); channel=INVALID_POSE_SOCKET; }
#ifdef _WIN32
    WSACleanup();
#endif
}
static int hex(char c) {
    if (c>='0' && c<='9') return c-'0';
    if (c>='a' && c<='f') return c-'a'+10;
    if (c>='A' && c<='F') return c-'A'+10;
    return -1;
}
static void initialize(void) {
    initialized=1;
    const char *enabled=getenv("CM64_POSE_ENABLE");
    const char *token=getenv("CM64_POSE_SESSION"), *port=getenv("CM64_POSE_PORT");
    if (!enabled || strcmp(enabled,"1") || !token || strlen(token)!=32 || !port) return;
    unsigned int nonzero=0;
    for (int i=0;i<16;i++) {
        int hi=hex(token[2*i]), lo=hex(token[2*i+1]);
        if (hi<0 || lo<0) return;
        session[i]=(unsigned char)((hi<<4)|lo); nonzero |= session[i];
    }
    if (!nonzero || !*port || strlen(port)>5) return;
    for (const char *p=port; *p; p++) if (*p<'0' || *p>'9') return;
    long number=strtol(port,NULL,10);
    if (number<1024 || number>65535) return;
#ifdef _WIN32
    WSADATA data;
    if (WSAStartup(MAKEWORD(2,2),&data)) return;
#endif
    channel=socket(AF_INET,SOCK_DGRAM,IPPROTO_UDP);
    if (channel==INVALID_POSE_SOCKET) { shutdown_pose(); return; }
#ifdef _WIN32
    u_long mode=1;
    if (ioctlsocket(channel,FIONBIO,&mode)) { shutdown_pose(); return; }
#else
    if (fcntl(channel,F_SETFL,O_NONBLOCK)<0) { shutdown_pose(); return; }
#endif
    memset(&destination,0,sizeof(destination));
    destination.sin_family=AF_INET;
    destination.sin_addr.s_addr=htonl(INADDR_LOOPBACK);
    destination.sin_port=htons((uint16_t)number);
    start_ms=monotonic_ms();
    atexit(shutdown_pose);
}
void cm64_pose_invalidate(void) { active=0; }
void cm64_pose(uint32_t tick, int16_t level, int16_t area,
               const float pos[3], const int16_t angles[3], uint32_t action, uint32_t flags) {
    if (!initialized) initialize();
    if (channel==INVALID_POSE_SOCKET || exhausted) return;
    uint64_t now=monotonic_ms();
    /* Finite run even if the collector disappears. No backlog or console output. */
    if (now<start_ms || now-start_ms>=300000 || sequence>=3000) {
        exhausted=1; shutdown_pose(); return;
    }
    if (!pos || !angles || level<=0 || area<=0 ||
        !isfinite(pos[0]) || !isfinite(pos[1]) || !isfinite(pos[2])) {
        cm64_pose_invalidate(); return;
    }
    if (!active || level!=last_level || area!=last_area) {
        if (generation==UINT32_MAX) { exhausted=1; shutdown_pose(); return; }
        ++generation; active=1; last_level=level; last_area=area;
    }
    if (sent && (now<last_ms || now-last_ms<100)) return;
    unsigned char packet[74]={'C','M','W','1',2,1,0,0};
    memcpy(packet+8,session,16);
    /* Explicit observer frame descriptor, NOT a native engine generation ID.
       M31A, native level s16, native area s16, reserved u32=0, observer epoch u32. */
    memcpy(packet+24,"M31A",4);
    be16(packet+28,(uint16_t)level); be16(packet+30,(uint16_t)area);
    be32(packet+36,generation);
    be32(packet+40,++sequence); be32(packet+44,tick);
    for (int i=0;i<3;i++) {
        uint32_t bits; memcpy(&bits,pos+i,4); be32(packet+48+i*4,bits);
        be16(packet+60+i*2,(uint16_t)angles[i]);
    }
    be32(packet+66,action); be32(packet+70,flags);
    last_ms=now; sent=1;
    (void)sendto(channel,(const char*)packet,sizeof(packet),0,
                 (const struct sockaddr*)&destination,sizeof(destination));
}
