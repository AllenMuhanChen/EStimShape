if ~exist('monkeyId','var')
    monkeyId = 4; % 4 is using when active experiments are on
end
    
if monkeyId == 1
    monkeyName = 'dobby';
elseif monkeyId == 2
    monkeyName = 'merri';
elseif monkeyId == 3
    monkeyName = 'gizmo';
else
    monkeyName = '';
end

oldPath = pwd;

analysisPath = fileparts(mfilename('fullpath'));
cd(analysisPath);
cd ..
rootPath = pwd;
stimPath = [rootPath '/stim/' monkeyName];
respPath = [rootPath '/resp/' monkeyName];
srcPath = [rootPath '/src'];
plotPath = [rootPath '/analysis/plots'];

% sessionsPath = ['/Users/' getenv('USER') '/Dropbox/documents/hopkins/nhp2pv4/projectV4Exploration/sessions'];
sessionsPath = [];

if isunix
    thumbPath = ['/Users/' getenv('USER') '/Dropbox/Documents/Hopkins/NHP2PV4/projectXper/3dma/xper_sach7/xper-sach/images'];
else
    thumbPath = 'C:\Users\Ram\Dropbox/Documents/Hopkins/NHP2PV4/projectXper/3dma/xper_sach7/xper-sach/images';
end
cd(oldPath);
clear oldPath pathstr;
