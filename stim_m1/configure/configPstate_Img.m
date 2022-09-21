function configPstate_Img
%periodic grater

global Pstate

Pstate = struct; %clear it

Pstate.param{1} = {'predelay'  'float'      2       0                'sec'};
Pstate.param{end+1} = {'postdelay'  'float'     2       0                'sec'};
Pstate.param{end+1} = {'stim_time'  'float'     1       0                'sec'};

Pstate.param{end+1} = {'x_pos'       'int'      600       0                'pixels'};
Pstate.param{end+1} = {'y_pos'       'int'      400       0                'pixels'};
Pstate.param{end+1} = {'size'      'float'      3       1                'deg'};

Pstate.param{end+1} = {'repopath'      'string'     '/home/m1_ram/Documents/imageRepository'       1                'pathname'};
Pstate.param{end+1} = {'imgbase1'      'string'     'medialAxis'       1                ''};
Pstate.param{end+1} = {'imgbase2'      'string'     'SHADE'       1                ''};
Pstate.param{end+1} = {'imgnr'      'int'     1       1                'img nr'};
