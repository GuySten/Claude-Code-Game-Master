/* setbfree_render - the rock organ played offline through setBfree's own DSP.
 *
 * SPDX-License-Identifier: GPL-2.0-or-later
 *
 * This file, unlike the rest of this repository, is licensed under the GNU General Public
 * License, version 2 or (at your option) any later version: it is compiled together with
 * setBfree's source (Copyright (C) 2003-2004 Fredrik Kilander, 2008-2018 Robin Gareus,
 * 2012 Will Panther; GPL-2.0-or-later) into one program, built in the engine's cache by
 * orchestra.fetch_setbfree and run as a separate process. Nothing else links to it.
 *
 * Copyright (C) 2026 the claude-code-game-master authors.
 *
 * This program is free software; you can redistribute it and/or modify it under the terms
 * of the GNU General Public License as published by the Free Software Foundation; either
 * version 2, or (at your option) any later version. It is distributed in the hope that it
 * will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License
 * for more details: <http://www.gnu.org/licenses/>.
 *
 * Usage: setbfree_render RATE OUT.f32 < events
 * Renders setBfree's tone generator -> preamp (overdrive) -> whirl (the Leslie), its reverb
 * left out, as 32-bit float stereo (interleaved, native byte order) to OUT.f32. The events,
 * one a line, in order:
 *   cfg KEY=VALUE      a setBfree configuration line (before any other line)
 *   bars 888800000     the upper manual's drawbars, 16' to 1'
 *   cc NAME VALUE      one of setBfree's MIDI control functions (0..127), e.g.
 *                      "cc overdrive.enable 127", "cc percussion.harmonic 0"
 *   speed 0|1          the rotary speaker slow or fast, already turning at that speed
 *   swell X            the swell pedal, 0..1 (eased there over ~30 ms)
 *   at FRAME           render up to this frame (setBfree works 128 frames at a time)
 *   on KEY / off KEY   a key of the upper manual (MIDI note number) down / up
 *   fast 0|1           the speaker switched slow / fast: it accelerates as setBfree's does
 *   end FRAME          render to here and stop
 */

#ifndef _GNU_SOURCE
#define _GNU_SOURCE
#endif

#include <locale.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "cfgParser.h"
#include "global_inst.h"
#include "main.h"
#include "midi.h"
#include "overdrive.h"
#include "program.h"
#include "reverb.h"
#include "state.h"
#include "tonegen.h"
#include "vibrato.h"
#include "whirl.h"

double SampleRateD = 44100.0;

int
mainConfig (ConfigContext* cfg)
{
	return 0;
}

const ConfigDoc*
mainDoc ()
{
	return NULL;
}

static b_instance inst;
static float      bufA[BUFFER_SIZE_SAMPLES], bufB[BUFFER_SIZE_SAMPLES];
static float      bufL[BUFFER_SIZE_SAMPLES], bufR[BUFFER_SIZE_SAMPLES];
static float      bufD[2][BUFFER_SIZE_SAMPLES];
static float      inter[2 * BUFFER_SIZE_SAMPLES];
static long       pos = 0;
static double     swell = 1.0, swellTarget = 1.0, swellStep = 0.01;

static void
block (FILE* out)
{
	struct b_tonegen* t = inst.synth;
	if (swell != swellTarget) { /* the foot moves: no step in level */
		double d = swellTarget - swell;
		swell    = fabs (d) <= swellStep ? swellTarget : swell + (d > 0 ? swellStep : -swellStep);
	}
	t->swellPedalGain = t->outputLevelTrim * swell;
	oscGenerateFragment (t, bufA, BUFFER_SIZE_SAMPLES);
	preamp (inst.preamp, bufA, bufB, BUFFER_SIZE_SAMPLES);
	whirlProc3 (inst.whirl, bufB, bufL, bufR, bufD[0], bufD[1], BUFFER_SIZE_SAMPLES);
	for (int i = 0; i < BUFFER_SIZE_SAMPLES; ++i) {
		inter[2 * i]     = bufL[i];
		inter[2 * i + 1] = bufR[i];
	}
	fwrite (inter, sizeof (float), 2 * BUFFER_SIZE_SAMPLES, out);
	pos += BUFFER_SIZE_SAMPLES;
}

static void
render_to (long frame, FILE* out)
{
	/* an event lands on the block boundary nearest its frame (within 1.5 ms) */
	while (pos + BUFFER_SIZE_SAMPLES / 2 <= frame) {
		block (out);
	}
}

static void
key (int down, int note)
{
	uint8_t msg[3] = { down ? 0x90 : 0x80, (uint8_t)(note & 0x7f), down ? 127 : 0 };
	parse_raw_midi_data (&inst, msg, 3);
}

static void
speed (int fast, int snap)
{
	struct b_whirl* w = inst.whirl;
	callMIDIControlFunction (inst.midicfg, "rotary.speed-preset", fast ? 127 : 0);
	if (snap) { /* already turning at that speed */
		w->hornIncr = w->hornTarget;
		w->drumIncr = w->drumTarget;
	}
}

int
main (int argc, char** argv)
{
	if (argc != 3) {
		fprintf (stderr, "usage: setbfree_render RATE OUT.f32 < events\n");
		return 2;
	}
	setlocale (LC_NUMERIC, "C");
	SampleRateD = atof (argv[1]);
	if (SampleRateD < 8000 || SampleRateD > 192000) {
		fprintf (stderr, "setbfree_render: bad rate %s\n", argv[1]);
		return 2;
	}
	FILE* out = fopen (argv[2], "wb");
	if (!out) {
		perror (argv[2]);
		return 1;
	}
	srand (1935); /* the key click's bursts: the same every time */
	swellStep = BUFFER_SIZE_SAMPLES / (0.03 * SampleRateD);

	inst.state   = allocRunningConfig ();
	inst.progs   = allocProgs ();
	inst.reverb  = allocReverb ();
	inst.whirl   = allocWhirl ();
	inst.midicfg = allocMidiCfg (inst.state);
	inst.synth   = allocTonegen ();
	inst.preamp  = allocPreamp ();
	initControllerTable (inst.midicfg);
	midiPrimeControllerMapping (inst.midicfg);

	char line[512];
	int  ready = 0;
	while (fgets (line, sizeof (line), stdin)) {
		char  word[32] = "";
		char* arg      = line;
		if (sscanf (line, "%31s", word) != 1) {
			continue;
		}
		arg += strspn (arg, " \t");
		arg += strlen (word);
		arg += strspn (arg, " \t");
		arg[strcspn (arg, "\r\n")] = 0;
		if (!strcmp (word, "cfg")) {
			if (ready) {
				fprintf (stderr, "setbfree_render: cfg after the organ was switched on\n");
				return 2;
			}
			parseConfigurationLine (&inst, "events", 0, arg);
			continue;
		}
		if (!ready) { /* the configuration read: switch the organ on */
			initToneGenerator (inst.synth, inst.midicfg);
			initVibrato (inst.synth, inst.midicfg);
			initPreamp (inst.preamp, inst.midicfg);
			initReverb (inst.reverb, inst.midicfg, SampleRateD);
			initWhirl (inst.whirl, inst.midicfg, SampleRateD);
			initRunningConfig (inst.state, inst.midicfg);
			initMidiTables (inst.midicfg);
			ready = 1;
		}
		if (!strcmp (word, "bars")) {
			unsigned int bars[9];
			for (int i = 0; i < 9; ++i) {
				bars[i] = (i < (int)strlen (arg) && arg[i] >= '0' && arg[i] <= '8') ? arg[i] - '0' : 0;
			}
			setDrawBars (&inst, 0, bars);
		} else if (!strcmp (word, "cc")) {
			char name[64];
			int  v;
			if (sscanf (arg, "%63s %d", name, &v) != 2) {
				fprintf (stderr, "setbfree_render: bad cc '%s'\n", arg);
				return 2;
			}
			callMIDIControlFunction (inst.midicfg, name, (unsigned char)(v < 0 ? 0 : v > 127 ? 127 : v));
		} else if (!strcmp (word, "speed")) {
			speed (atoi (arg), 1);
		} else if (!strcmp (word, "swell")) {
			swellTarget = fmax (0.0, fmin (1.0, atof (arg)));
			if (pos == 0) {
				swell = swellTarget;
			}
		} else if (!strcmp (word, "at")) {
			render_to (atol (arg), out);
		} else if (!strcmp (word, "on") || !strcmp (word, "off")) {
			key (word[1] == 'n', atoi (arg));
		} else if (!strcmp (word, "fast")) {
			speed (atoi (arg), 0);
		} else if (!strcmp (word, "end")) {
			long end = atol (arg);
			while (pos < end) {
				block (out);
			}
			break;
		} else {
			fprintf (stderr, "setbfree_render: unknown event '%s'\n", word);
			return 2;
		}
	}
	if (fclose (out)) {
		perror (argv[2]);
		return 1;
	}
	return 0;
}
