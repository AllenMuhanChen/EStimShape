function configSync

global daq

daq = DaqDeviceIndex;

if ~isempty(daq)
    DaqDConfigPort(daq,0,1);    
    DaqDConfigPort(daq,1,1);    
else
    disp('Daq device does not appear to be connected');
end