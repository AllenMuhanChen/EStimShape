function configPstate_GraterRamp
%periodic grater

global Pstate

Pstate = struct; %clear it

Pstate.param{1} = {'predelay'  'float'      2       0                'sec'};
Pstate.param{2} = {'postdelay'  'float'     2       0                'sec'};
Pstate.param{3} = {'stim_time'  'float'     9       0                'sec'};

Pstate.param{4} = {'x_pos'       'int'      600       0                'pixels'};
Pstate.param{5} = {'y_pos'       'int'      400       0                'pixels'};
Pstate.param{6} = {'x_size'      'float'      3       1                'deg'};
Pstate.param{7} = {'y_size'      'float'      3       1                'deg'};
Pstate.param{8} = {'mask_type'   'string'   'none'       0                ''};
Pstate.param{9} = {'mask_radius' 'float'      6       1                'deg'};
Pstate.param{10} = {'x_zoom'      'int'   1       0                ''};
Pstate.param{11} = {'y_zoom'      'int'   1       0                ''};

Pstate.param{12} = {'altazimuth'      'string'   'none'       0                ''};
Pstate.param{13} = {'tilt_alt'         'int'        0       0                'deg'};
Pstate.param{14} = {'tilt_az'         'int'        0       0                'deg'};
Pstate.param{15} = {'dx_perpbis'         'float'        0       0                'cm'};
Pstate.param{16} = {'dy_perpbis'         'float'        0       0                'cm'};

Pstate.param{17} = {'contrast_min'    'float'     0       0                '%'};
Pstate.param{18} = {'contrast_max'    'float'     100       0                '%'};
Pstate.param{19} = {'Ncontrast'    'int'     5       0                ''};

Pstate.param{20} = {'ori'         'int'        0       0                'deg'};
Pstate.param{21} = {'phase'         'float'        0       0                'deg'};

Pstate.param{22} = {'st_profile'  'string'   'sin'       0                ''};
Pstate.param{23} = {'s_freq'      'float'      1      -1                 'cyc/deg'};
Pstate.param{24} = {'s_profile'   'string'   'sin'       0                ''};
Pstate.param{25} = {'s_duty'      'float'   0.5       0                ''};
Pstate.param{26} = {'t_profile'   'string'   'sin'       0                ''};
Pstate.param{27} = {'t_duty'      'float'   0.5       0                ''};
Pstate.param{28} = {'t_period'    'int'       20       0                'frames'};

Pstate.param{29} = {'background'      'int'   128       0                ''};

Pstate.param{30} = {'redgain' 'float'   1       0             ''};
Pstate.param{31} = {'greengain' 'float'   1       0             ''};
Pstate.param{32} = {'bluegain' 'float'   1       0             ''};
Pstate.param{33} = {'redbase' 'float'   .5       0             ''};
Pstate.param{34} = {'greenbase' 'float'   .5       0             ''};
Pstate.param{35} = {'bluebase' 'float'   .5       0             ''};
Pstate.param{36} = {'colormod'    'int'   1       0                ''};

Pstate.param{37} = {'contrast'    'float'     100       0                '%'};



