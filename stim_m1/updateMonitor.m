function updateMonitor


global Mstate screenPTR 


switch Mstate.monitor
    
    case 'LCD' %60Hz
        
        Mstate.screenXcm = 54.5; %1920 pixel
        Mstate.screenYcm = 30; %1080 pixel
        
       load('/Stimulator_slave/calibration/ACER 3-24-15/luminance.mat','bufLUT')
%         load('/Stimulator_slave/calibration/LCD 5-3-10 PR650/luminance.mat','bufLUT')
        
        %bufLUT = (0:255)/255;
        % bufLUT = bufLUT'*[1 1 1];
        
         
    case 'VPX' %120Hz
        
        Mstate.screenXcm = 52; %1920 pixel
        Mstate.screenYcm = 29.5; %1080 pixel
        
%        load('/Stimulator_slave/calibration/ACER 2-4-13/luminance.mat','bufLUT')
%         load('/Stimulator_slave/calibration/LCD 5-3-10 PR650/luminance.mat','bufLUT')
        
        bufLUT = (0:255)/255;
         bufLUT = bufLUT'*[1 1 1];
         bufLUT=bufLUT.^(1/2.2);
        
    case 'CRT'
        
        %Actual screen width
        %Mstate.screenXcm = 32.5;
        %Mstate.screenYcm = 24;
        
        %Display size
        %Mstate.screenXcm = 30.5;
        Mstate.screenXcm = 40.6;  %to make the pixels square
        Mstate.screenYcm = 30.5;  
        
        %load('/Matlab_code/calibration_stuff/measurements/CRT 5-18-10 PR650/LUT.mat','bufLUT')
        %load('/Matlab_code/calibration_stuff/measurements/CRT 6-9-10 UDT/LUT.mat','bufLUT')
        
        %This one is only slightly different than the UDT measurement, but
        %occured after I changed the monitor cable, which eliminated the
        %aliasing.
        bufLUT = (0:255)/255;
        bufLUT = bufLUT'*[1 1 1];
        
    case 'LIN'   %load a linear table
        
        Mstate.screenXcm = 54.5;
        Mstate.screenYcm = 30;        
        
        bufLUT = (0:255)/255;
        bufLUT = bufLUT'*[1 1 1];
        
   case 'TEL'   %load a linear table
        
        Mstate.screenXcm = 121;
        Mstate.screenYcm = 68.3;        
        
        load('/Matlab_code/calibration_stuff/measurements/TELEV 9-29-10/LUT.mat','bufLUT')
        
end


Screen('LoadNormalizedGammaTable', screenPTR, bufLUT);  %gamma LUT

