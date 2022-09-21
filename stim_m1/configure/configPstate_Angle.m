function configPstate_Angle
%periodic grater

global Pstate

Pstate = struct; %clear it

Pstate.param{1} = {'predelay'  'float'      2       0                'sec'};
Pstate.param{2} = {'postdelay'  'float'     2       0                'sec'};
Pstate.param{3} = {'stim_time'  'float'     1       0                'sec'};

Pstate.param{4} = {'x_pos'       'int'      600       0                'pixels'};
Pstate.param{5} = {'y_pos'       'int'      400       0                'pixels'};
Pstate.param{6} = {'radius'      'float'      3       1                'deg'};


Pstate.param{7} = {'stimori'      'int'     0       1                'deg'};
Pstate.param{8} = {'stimacute'      'int'     45       1                'deg'};
Pstate.param{9} = {'stimcurve'      'float'     1       1                ''};
Pstate.param{10} = {'stimtype'      'int'     1       1                '1 CV, 2 CC'};

Pstate.param{11} = {'background'      'int'   128       0                ''};
Pstate.param{12} = {'redgain' 'float'   1       0             ''};
Pstate.param{13} = {'greengain' 'float'   1       0             ''};
Pstate.param{14} = {'bluegain' 'float'   1       0             ''};
Pstate.param{15} = {'contrast' 'float'   100       0             '%'};
Pstate.param{16} = {'mouse_bit'    'int'   0       0                ''};

