function configPstate_OpticFlow
%optic flow stim

global Pstate

Pstate = struct; %clear it

Pstate.type = 'OF';

Pstate.param{1} = {'predelay'  'float'      2       0                'sec'};
Pstate.param{2} = {'postdelay'  'float'     2       0                'sec'};
Pstate.param{3} = {'stim_time'  'float'     1       0                'sec'};

Pstate.param{4} = {'x_pos'       'int'      600       0                'pixels'};
Pstate.param{5} = {'y_pos'       'int'      400       0                'pixels'};
Pstate.param{6} = {'stimRadius' 'float'      6       1                'deg'};

Pstate.param{7} = {'stimType'   'int'      1       1                'Rand, Tx, Ty, C, R'};
Pstate.param{8} = {'stimDir'   'int'      1       1                '1, -1'};
Pstate.param{9} = {'dotDensity'      'float'      100       1                'dots/(deg^2 s)'};
Pstate.param{10} = {'sizeDots'      'float'     0.2       1                'deg'};
Pstate.param{11} = {'speedDots'      'float'     5       1                'deg/s'};
Pstate.param{12} = {'dotLifetime'      'int'     0       1                'frames, 0 inf'};
Pstate.param{13} = {'dotCoherence'      'int'     100       1                '%'};
Pstate.param{14} = {'dotType'      'int'     0       1                'sq, circ'};
   
Pstate.param{15} = {'background'      'int'   128       0                ''};
Pstate.param{16} = {'redgun' 'int'   255       0             ''};
Pstate.param{17} = {'greengun' 'int'   255       0             ''};
Pstate.param{18} = {'bluegun' 'int'   255       0             ''};
Pstate.param{19} = {'contrast'    'float'     100       0                '%'};
Pstate.param{20} = {'mouse_bit'    'int'   0       0                ''};


