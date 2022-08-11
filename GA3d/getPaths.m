oldPath = pwd;

srcPath = fileparts(mfilename('fullpath'));
cd(srcPath);
cd ..
rootPath = pwd;
stimPath = [rootPath '/stim'];
respPath = [rootPath '/resp'];
logPath = [rootPath '/log'];
plotPath = [rootPath '/plots'];
analysisPath = [rootPath '/analysis'];

% sessionsPath = ['/Users/' getenv('USER') '/Dropbox/documents/hopkins/nhp2pv4/projectV4Exploration/sessions'];
sessionsPath = [];

if strcmp(getenv('OS'),'Windows_NT')
    secondaryPath = 'X:\Ramanujan\projectMaskedGA3D';
else
    secondaryPath = '/Volumes/ConnorHome-1/Ramanujan/projectMaskedGA3D';
    if ~exist(secondaryPath,'dir')
        secondaryPath = '/Volumes/ConnorHome/Ramanujan/projectMaskedGA3D';
        if ~exist(secondaryPath,'dir')
            disp('Mounting NAS...');
            system('open ''afp://ConnorLab:Whedon101@172.30.6.102/ConnorHome/''');
            tryCount = 0;
            while ~exist(secondaryPath,'dir') && tryCount < 40
                pause(0.5);
                tryCount = tryCount + 1;
            end

            if tryCount == 40
                while ~exist(secondaryPath,'dir')
                    disp('Could not automatically mount NAS. Please manually mount and press enter.')
                    pause;
                end
            end
        end
        
    end
end



cd(oldPath);
clear oldPath pathstr;
