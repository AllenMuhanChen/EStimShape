function configPstate_perGrater
%periodic grater

global Pstate

Pstate = struct; %clear it

Pstate.param{1} = {'predelay'  'float'      2       0                'sec'};
Pstate.param{2} = {'postdelay'  'float'     2       0                'sec'};
Pstate.param{3} = {'stim_time'  'float'     1       0                'sec'};

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

Pstate.param{17} = {'contrast'    'float'     100       0                '%'};
Pstate.param{18} = {'ori'         'int'        0       0                'deg'};
Pstate.param{19} = {'phase'         'float'        0       0                'deg'};

Pstate.param{20} = {'separable'   'int'     0       0                'bit'};
Pstate.param{21} = {'st_profile'  'string'   'sin'       0                ''};
Pstate.param{22} = {'s_freq'      'float'      1      -1                 'cyc/deg'};
Pstate.param{23} = {'s_profile'   'string'   'sin'       0                ''};
Pstate.param{24} = {'s_duty'      'float'   0.5       0                ''};
Pstate.param{25} = {'t_profile'   'string'   'sin'       0                ''};
Pstate.param{26} = {'t_duty'      'float'   0.5       0                ''};
Pstate.param{27} = {'t_period'    'int'       20       0                'frames'};

Pstate.param{28} = {'background'      'int'   128       0                ''};

Pstate.param{29} = {'noise_bit'      'int'   0       0                ''};
Pstate.param{30} = {'noise_amp'      'float'   100       0                '%'};
Pstate.param{31} = {'noise_width'    'int'   5       0                'deg'};
Pstate.param{32} = {'noise_lifetime' 'float'   10       0             'frames'};
Pstate.param{33} = {'noise_type' 'string'   'random'       0             ''};

Pstate.param{34} = {'redgain' 'float'   1       0             ''};
Pstate.param{35} = {'greengain' 'float'   1       0             ''};
Pstate.param{36} = {'bluegain' 'float'   1       0             ''};
Pstate.param{37} = {'redbase' 'float'   .5       0             ''};
Pstate.param{38} = {'greenbase' 'float'   .5       0             ''};
Pstate.param{39} = {'bluebase' 'float'   .5       0             ''};
Pstate.param{40} = {'colormod'    'int'   1       0                ''};

Pstate.param{41} = {'mouse_bit'    'int'   0       0                ''};
Pstate.param{42} = {'avg_bit'    'int'   0       0                ''};


Pstate.param{43} = {'eye_bit'    'int'   1       0                ''};
Pstate.param{44} = {'Leye_bit'    'int'   1       0                ''};
Pstate.param{45} = {'Reye_bit'    'int'   1       0                ''};

Pstate.param{46} = {'plaid_bit'    'int'   0       0                ''};
Pstate.param{47} = {'contrast2'    'float'     10       0                '%'};
Pstate.param{48} = {'ori2'         'int'        90       0                'deg'};
Pstate.param{49} = {'phase2'         'float'        0       0                'deg'};
Pstate.param{50} = {'st_profile2'  'string'   'sin'       0                ''};
Pstate.param{51} = {'s_freq2'      'float'      1      -1                 'cyc/deg'};
Pstate.param{52} = {'s_profile2'   'string'   'sin'       0                ''};
Pstate.param{53} = {'s_duty2'      'float'   0.5       0                ''};
Pstate.param{54} = {'t_profile2'   'string'   'sin'       0                ''};
Pstate.param{55} = {'t_duty2'      'float'   0.5       0                ''};
Pstate.param{56} = {'t_period2'    'int'       20       0                'frames'};
