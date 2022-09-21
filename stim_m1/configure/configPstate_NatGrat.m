function configPstate_NatGrat
%periodic grater

global Pstate

Pstate = struct; %clear it

Pstate.param{1} = {'predelay'  'float'      2       0                'sec'};
Pstate.param{2} = {'postdelay'  'float'     2       0                'sec'};
Pstate.param{3} = {'stim_time'  'float'     1       0                'sec'};

Pstate.param{4} = {'x_pos'       'int'      600       0                'pixels'};
Pstate.param{5} = {'y_pos'       'int'      400       0                'pixels'};
Pstate.param{6} = {'x_px'      'int'      256       1                'deg'};
Pstate.param{7} = {'y_px'      'int'      256       1                'deg'};

Pstate.param{8} = {'cond'      'int'     1       1                ''};

Pstate.param{9} = {'background'      'int'   128       0                ''};
Pstate.param{10} = {'contrast' 'float'   100       0             '%'};


