
% Spatial calibration

global scanbox_h sbconfig calibration objective_h

cal_org = calibration;  % save whatever calibration is there now...

h = guihandles(scanbox_h);

delta = [100 100 80 70 60 50 40 35 30 25 20 20 15]; % deltas for each mag

% set some vars...

h.frames.String = '120'; h.frames.Callback(h.frames,[]);
h.animal.String = 'xx0'; h.animal.Callback(h.animal,[]);
h.unit.String = '000';   h.unit.Callback(h.unit,[]);
h.expt.String = '000';   h.expt.Callback(h.unit,[]);

cd([h.dirname.String '\' h.animal.String]);

[~,~] = system('del xx0*');                                 % removes xx0 files

tri_send('KBY',0,12,0); % set knobby to super fine

h.tfilter.Value = 3; h.tfilter.Callback(h.tfilter,[]);

% Get the button
g = findobj(scanbox_h,'tag','grabb');

h.returnbox.Value=1; h.returnbox.Callback(h.returnbox,[]);
h.knobby_enable.Value = 1; h.knobby_enable.Callback(h.knobby_enable,[]);

for mag = 1:13
    % delta(mag) = round(100/str2double(h.magnification.String(h.magnification.Value,:)));
    h.knobby_table.Data = [delta(mag) delta(mag) 0 0 60];
    m = findobj(scanbox_h,'tag','magnification');
    h.magnification.Value = mag; h.magnification.Callback(h.magnification,[]);
    h.grabb.Callback(h.grabb,[]);
    pause(2);
    h.knobby_enable.Value = 1; h.knobby_enable.Callback(h.knobby_enable,[]);
end

% process

clear calibration;
for mag = 1:13
    fn = sprintf('xx0_000_%03d',mag-1);
    z0 = sbxread(fn,30,30);      % to allow mirror warmup
    z1 = sbxread(fn,80,30);
    z0 = squeeze(mean(z0(1,:,:,:),4));
    z1 = squeeze(mean(z1(1,:,:,:),4));
    [u,v] = fftalign(z0,z1); 
    calibration(mag).uv = [u v];
    calibration(mag).delta = delta(mag);
    calibration(mag).x = delta(mag)/v;
    calibration(mag).y = delta(mag)/u;
    calibration(mag).gain_resonant_mult = sbconfig.gain_resonant_mult;          % same for all (for now...)
end

fclose('all');
global info
info = [];

cal_org{objective_h.Value} = calibration;         % insert calibration into appropiate objective entry
calibration = cal_org;

objective_h.Callback(objective_h,[]);

sbxroot = fileparts(which('scanbox'));
save([sbxroot '\sbxcal.mat'],'calibration'); % save the calibration in the core directory

ccal = cal_org{objective_h.Value};
warndlg({sprintf('Calibration for %s complete and saved!',objective_h.String{objective_h.Value});...
    sprintf('Optimal value of gain_resonant_mult is %.3f to achieve aspect ratio = 1',median([ccal.x]./[ccal.y])*sbconfig.gain_resonant_mult); ...
    'You must re-calibrate for each objective if you decide to change it';
    'Calibration will take effect after restarting Scanbox'});

