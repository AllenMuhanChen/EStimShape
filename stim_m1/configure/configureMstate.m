function configureMstate

global Mstate

Mstate.anim = 'merri';

Mstate.unit = datestr(now,'yymmdd');

% sessNum = input('Session Number: ');
Mstate.expt = '1';

Mstate.hemi = 'right';
Mstate.screenDist = 50;

Mstate.monitor = 'CRT';  %This should match the default at the master. Otherwise, they will differ, but only at startup

%'updateMonitor.m' happens in 'screenconfig.m' at startup

Mstate.running = 0;

Mstate.syncSize = 4;  %cm
