function configPstate_DualGrater

global Pstate

Pstate = struct; %clear it

Pstate.param{1} = {'predelay'  'float'      2       0                'sec'};
Pstate.param{2} = {'postdelay'  'float'     2       0                'sec'};
Pstate.param{3} = {'stim_time'  'float'     1       0                'sec'};

Pstate.param{4} = {'x_pos'       'int'      600       0                'pixels'};
Pstate.param{5} = {'y_pos'       'int'      400       0                'pixels'};
Pstate.param{6} = {'x_size'      'float'      7       1                'deg'};
Pstate.param{7} = {'y_size'      'float'      7       1                'deg'};
Pstate.param{8} = {'mask_radius' 'float'      3       1                'deg'};


Pstate.param{9} = {'background'      'int'   128       0                ''};
Pstate.param{10} = {'contrast'    'float'     100       0                '%'};

Pstate.param{11} = {'ori'         'int'        0       0                'deg'};

Pstate.param{12} = {'h_per'      'int'   30       0                'frames'};
Pstate.param{13} = {'n_ori'    'int'   8       0                ''};
Pstate.param{14} = {'n_phase' 'int'   4       0             ''};

Pstate.param{15} = {'min_sf'   'float'   1       0                ''};
Pstate.param{16} = {'max_sf'   'float'   1       0                ''};
Pstate.param{17} = {'n_sfreq' 'int'   1       0             ''};
Pstate.param{18} = {'sf_domain'   'string'   'log'       0                ''};
Pstate.param{19} = {'s_profile'   'string'   'sin'       0                ''};
Pstate.param{20} = {'s_duty'      'float'   0.5       0                ''};

Pstate.param{21} = {'redgain' 'float'   1       0             ''};
Pstate.param{22} = {'greengain' 'float'   1       0             ''};
Pstate.param{23} = {'bluegain' 'float'   1       0             ''};
Pstate.param{24} = {'redbase' 'float'   .5       0             ''};
Pstate.param{25} = {'greenbase' 'float'   .5       0             ''};
Pstate.param{26} = {'bluebase' 'float'   .5       0             ''};
Pstate.param{27} = {'colorspace' 'string'   'gray'       0             ''};


Pstate.param{28} = {'rseed'    'int'   1       0                ''};

Pstate.param{29} = {'blankProb'    'float'   0       0                ''};

Pstate.param{30} = {'CFSstim_mon'    'int'   0       0                'L R'};
Pstate.param{31} = {'CFSmask_mon'    'int'   0       0                'L R'};
Pstate.param{32} = {'CFSstim_bit' 'int'   1       0                'bit'};
Pstate.param{33} = {'CFSmask_bit' 'int'   0       0                'bit'};
Pstate.param{34} = {'CFSmask_type' 'string'   'gray_circles'   0  ''};
Pstate.param{35} = {'CFSx_size' 'float'   9   0  ''};
Pstate.param{36} = {'CFSy_size' 'float'   9   0  ''};
Pstate.param{37} = {'CFSin_radius' 'float'   3   0  ''};
Pstate.param{38} = {'CFSout_radius' 'float'   5   0  ''};
Pstate.param{39} = {'CFSn_mask' 'int'   100   0  ''};
Pstate.param{40} = {'CFSh_per' 'int'   100   6  'frames'};

