oldPath = pwd;

analysisPath = fileparts(mfilename('fullpath'));
cd(analysisPath);
cd ..
rootPath = pwd;
stimPath = [rootPath '/stim/dobby'];
respPath = [rootPath '/resp/dobby'];
srcPath = [rootPath '/src/dobby'];
plotPath = [rootPath '/analysis/plots'];

% sessionsPath = ['/Users/' getenv('USER') '/Dropbox/documents/hopkins/nhp2pv4/projectV4Exploration/sessions'];
sessionsPath = [];

thumbPath = ['/Users/' getenv('USER') '/Dropbox/Documents/Hopkins/NHP2PV4/projectXper/3dma/xper_sach7/xper-sach/images/dobby'];

cd(oldPath);
clear oldPath pathstr;
