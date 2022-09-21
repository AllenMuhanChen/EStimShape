function configPstate_Gabor
%periodic grater

global Pstate

Pstate = struct; %clear it

Pstate.param{1}     = {'predelay'   'float'     2       0       'sec'};
Pstate.param{end+1} = {'postdelay'  'float'     2       0       'sec'};
Pstate.param{end+1} = {'stim_time'  'float'     1       0       'sec'};

Pstate.param{end+1} = {'x_pos'      'int'       600     0       'pixels'};
Pstate.param{end+1} = {'y_pos'      'int'       400     0       'pixels'};
Pstate.param{end+1} = {'ori'        'float'     90      1       'deg'};
Pstate.param{end+1} = {'sw'         'float'     3       1       'deg'};
Pstate.param{end+1} = {'phase'      'float'     0       1       'deg'};
Pstate.param{end+1} = {'siz'        'float'     2       1       'deg'};
Pstate.param{end+1} = {'cont'       'float'     1       1       'deg'};
Pstate.param{end+1} = {'aRatio'     'float'     1       1       'deg'};
Pstate.param{end+1} = {'col1'       'float'     0       1       'deg'};
Pstate.param{end+1} = {'col2'       'float'     1       1       'deg'};