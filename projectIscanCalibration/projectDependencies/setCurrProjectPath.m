function setCurrProjectPath()
    clc;
    if strcmp(getenv('OS'),'Windows_NT')
    	cd('C:\Users\a1_ram\Dropbox\Documents\Hopkins\NHP2PV4\projectIscanCalibration')
    else
    	cd(['/Users/' getenv('USER') '/Dropbox/Documents/Hopkins/NHP2PV4/projectMaskedGA3D/src'])
    end
end
