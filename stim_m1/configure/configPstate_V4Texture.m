function configPstate_V4Texture
%periodic grater

global Pstate

Pstate = struct; %clear it

Pstate.type='FP';

Pstate.param{1} = {'predelay'  'float'      2       0                'sec'};
Pstate.param{2} = {'postdelay'  'float'     2       0                'sec'};
Pstate.param{3} = {'stim_time'  'float'     1       0                'sec'};

Pstate.param{4} = {'x_pos'       'int'      600       0                'pixels'};
Pstate.param{5} = {'y_pos'       'int'      400       0                'pixels'};
Pstate.param{6} = {'x_size'      'int'      600       1                'pixels'};
Pstate.param{7} = {'y_size'      'int'      600       1                'pixels'};


Pstate.param{8} = {'maxsize'      'int'     512       1                'pixels'};
Pstate.param{9} = {'minsize'      'int'     32       1                'pixels'};
Pstate.param{10} = {'maxcyc'      'int'     16       1                'pixels'};
Pstate.param{11} = {'mincyc'      'int'     512       1                'pixels'};
Pstate.param{12} = {'maxconc'       'int'   5       1                  ''};
Pstate.param{13} = {'minvel'      'float'     0       1                ''};
Pstate.param{14} = {'maxvel'      'float'     0.5       1                ''};
Pstate.param{15} = {'grdensity'      'int'     3       1                ''};
Pstate.param{16} = {'colorbit'      'int'     1       1                '0, 1'};
Pstate.param{17} = {'background'      'int'   128       0                ''};
Pstate.param{18} = {'contrast'    'float'     100       0                '%'};




