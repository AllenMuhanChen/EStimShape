function playbox

global screenNum Mstate screenPTR

Pstruct = getParamStruct;
screenRes = Screen('Resolution',screenNum);

barWcm = 2*Mstate.screenDist*tan(Pstruct.barWidth/2*pi/180)  %bar width in cm
barLcm = 2*Mstate.screenDist*tan(Pstruct.barLength/2*pi/180)  %bar length in cm

Im = makeBar(barWcm,barLcm,Pstruct.ori,screenRes);
Im = Im*Pstruct.contrast/100;

gray = 127;
amp = 128;
Gtxtr = Screen(screenPTR, 'MakeTexture', gray+amp*Im);  %Dark Bar
TDim = size(Im);

for i = 1:100
    Screen('DrawTextures', screenPTR, Gtxtr,[0 0 TDim(2)-1 TDim(1)-1]',...
        [300 500 300+TDim(2) 500+TDim(1)]');
    
    Screen(screenPTR, 'Flip');
end

Screen('Close')  %Get rid of all textures/offscreen windows