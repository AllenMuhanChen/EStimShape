function configPstate_GATexture
%periodic grater

global Pstate

Pstate = struct; %clear it

Pstate.param{1} = {'predelay'  'float'      1       0                'sec'};
Pstate.param{2} = {'postdelay'  'float'     1       0                'sec'};
Pstate.param{3} = {'stim_time'  'float'     0.5       0                'sec'};

Pstate.param{4} = {'x_pos'       'int'      1000       0                'pixels'};
Pstate.param{5} = {'y_pos'       'int'      700       0                'pixels'};
Pstate.param{6} = {'xysize'      'float'      5       0                'deg'};
Pstate.param{7} = {'masksize'      'float'      6       0                'deg'};

Pstate.param{8} = {'stimpath'      'string'     '/Volumes/NielsenHome/Matlab/GA/project2PGA/stim/'       1                ''};
Pstate.param{9} = {'GArun'      'int'     1       1                ''};
Pstate.param{10} = {'genNum'      'int'     1       1                ''};
Pstate.param{11} = {'linNum'      'int'     1       1                ''};
Pstate.param{12} = {'stimnr'      'int'     1       1                ''};

Pstate.param{13} = {'useBubbles'      'int'     0       1                ''};
Pstate.param{14} = {'numBestStimBubbles'      'int'     4       1                ''};

Pstate.param{15} = {'fore_r'      'float'      1       0                ''};
Pstate.param{16} = {'fore_g'      'float'      1       0                ''};
Pstate.param{17} = {'fore_b'      'float'      1       0                ''};

Pstate.param{18} = {'maskcolor'      'int'   128       0                ''};
Pstate.param{19} = {'background'      'int'   0       0                ''};
Pstate.param{20} = {'contrast' 'float'   100       0             '%'};


