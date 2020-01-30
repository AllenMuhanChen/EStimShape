/*
 * bindcpu.c
 *
 *  Created on: Nov 4, 2009
 *      Author: wang
 */

#if defined(LINUX)

#include <jni.h>

#ifndef __USE_GNU
#define __USE_GNU
#endif

#include <stdio.h>
#include <sched.h>
#include <stdlib.h>
#include <errno.h>
#include <string.h>
#include <sys/time.h>

int set_cpu_affinity (pid_t pid, unsigned long mask) {
	cpu_set_t cpu_mask;
#ifdef CPU_ZERO
	CPU_ZERO(&cpu_mask);
#else
	__CPU_ZERO(&cpu_mask);
#endif
	cpu_mask.__bits[0] = mask;
	int ret = sched_setaffinity(pid, sizeof(cpu_mask), &cpu_mask);
	return ret;
}

unsigned long get_cpu_affinity(pid_t pid) {
	cpu_set_t cpu_mask;
	int ret = sched_getaffinity(pid, sizeof(cpu_mask), &cpu_mask);
	if (ret != 0) {
		fprintf(stderr, "Error getting CPU affinity: %d\n", ret);
		return -1;
	}
	return cpu_mask.__bits[0];
}

#endif

int main(int argc, char *argv[]) {
#if defined(LINUX)

	unsigned long new_mask;
	unsigned long cur_mask;
	pid_t pid;

	if (argc != 3) {
		printf("usage: %s [pid] [cpu_mask]\n", argv[0]);
		return -1;
	}

	pid = atol(argv[1]);
	sscanf(argv[2], "%08lx", &new_mask);

	cur_mask = get_cpu_affinity(pid);
	printf("pid %d's old affinity: %08lx\n", pid, cur_mask);

	int ret = set_cpu_affinity (pid, new_mask);
	if (ret != 0) {
		printf("Error setting CPU affinity: %d\n", ret);
	}

	cur_mask = get_cpu_affinity(pid);
	printf("pid %d's new affinity: %08lx\n", pid, cur_mask);

#endif
	return 0;
}
