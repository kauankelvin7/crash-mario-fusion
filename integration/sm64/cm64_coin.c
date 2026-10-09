/* Observe an existing native coin interaction. No game assets or replacement physics. */
#include "cm64_coin.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#ifdef _WIN32
#include <winsock2.h>
#include <windows.h>
typedef SOCKET socket_type;
#define BAD_SOCKET INVALID_SOCKET
#else
#include <sys/socket.h>
#include <netinet/in.h>
#include <fcntl.h>
#include <unistd.h>
typedef int socket_type;
#define BAD_SOCKET (-1)
#endif
_Static_assert(sizeof(float) == 4, "Protocol requires 32-bit float");
static socket_type channel = BAD_SOCKET;
static int initialized;
static unsigned char session[16];
static uint32_t sequence;
static struct sockaddr_in destination;
static void be32(unsigned char *p, uint32_t v) {
    p[0]=(unsigned char)(v>>24); p[1]=(unsigned char)(v>>16);
    p[2]=(unsigned char)(v>>8); p[3]=(unsigned char)v;
}
static uint64_t unix_ms(void) {
#ifdef _WIN32
    FILETIME ft; ULARGE_INTEGER value;
    GetSystemTimeAsFileTime(&ft);
    value.LowPart=ft.dwLowDateTime; value.HighPart=ft.dwHighDateTime;
    return (value.QuadPart-116444736000000000ULL)/10000ULL;
#else
    struct timespec value;
    if (timespec_get(&value, TIME_UTC) != TIME_UTC) return 0;
    return (uint64_t)value.tv_sec*1000+(uint64_t)value.tv_nsec/1000000;
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
    const char *token=getenv("CM64_SESSION"), *port_text=getenv("CM64_PORT");
    if (!token || !port_text) return; /* Same executable can run a passive baseline. */
    if (strlen(token)!=32) { fprintf(stderr,"[cm64] invalid session\n"); return; }
    for (int i=0;i<16;i++) {
        int hi=hex(token[2*i]), lo=hex(token[2*i+1]);
        if (hi<0 || lo<0) { fprintf(stderr,"[cm64] invalid session\n"); return; }
        session[i]=(unsigned char)((hi<<4)|lo);
    }
    char *end; long port=strtol(port_text,&end,10);
    if (!*port_text || *end || port<1024 || port>65535) {
        fprintf(stderr,"[cm64] invalid port\n"); return;
    }
#ifdef _WIN32
    WSADATA data;
    if (WSAStartup(MAKEWORD(2,2),&data)!=0) return;
#endif
    channel=socket(AF_INET,SOCK_DGRAM,IPPROTO_UDP);
    if (channel==BAD_SOCKET) { fprintf(stderr,"[cm64] socket failed\n"); return; }
#ifdef _WIN32
    u_long mode=1;
    if (ioctlsocket(channel,FIONBIO,&mode)!=0) {
        closesocket(channel); channel=BAD_SOCKET; return;
    }
#else
    if (fcntl(channel,F_SETFL,O_NONBLOCK)<0) {
        close(channel); channel=BAD_SOCKET; return;
    }
#endif
    memset(&destination,0,sizeof(destination));
    destination.sin_family=AF_INET; destination.sin_port=htons((uint16_t)port);
    destination.sin_addr.s_addr=htonl(INADDR_LOOPBACK);
    fprintf(stderr,"[cm64] native coin observer enabled, UDP loopback port=%ld\n",port);
}
void cm64_coin(uint32_t native_tick, int32_t coins, float x, float y, float z) {
    if (!initialized) initialize();
    if (channel==BAD_SOCKET || sequence==UINT32_MAX) return;
    unsigned char packet[52]={ 'C','M','J','1' };
    memcpy(packet+4,session,16);
    be32(packet+20,++sequence); be32(packet+24,native_tick);
    be32(packet+28,(uint32_t)coins);
    float position[3]={x,y,z};
    for (int i=0;i<3;i++) { uint32_t bits; memcpy(&bits,&position[i],4); be32(packet+32+4*i,bits); }
    uint64_t timestamp=unix_ms(); be32(packet+44,(uint32_t)(timestamp>>32)); be32(packet+48,(uint32_t)timestamp);
    int result=(int)sendto(channel,(const char*)packet,sizeof(packet),0,
                          (const struct sockaddr*)&destination,sizeof(destination));
    fprintf(stderr,"[cm64] coin seq=%u native_tick=%u coins=%d pos=%.3f,%.3f,%.3f sent=%d\n",
            sequence,native_tick,coins,x,y,z,result);
    /* No retry or waiting on the native gameplay thread. */
}
