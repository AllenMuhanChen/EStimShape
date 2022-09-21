%%we're using the brodartz texture database
function makeGAManualMapper

global Gtxtr Mstate screenPTROff2 screenNum screenPTR

Screen('Close')  %First clean up: Get rid of all textures/offscreen windows

Gtxtr = [];   %reset
screenPTROff2=Screen('OpenOffscreenWindow',screenPTR);
% screenPTROff2=Screen('OpenOffscreenWindow',screenPTR,[],[],[],[],8);
Screen(screenPTROff2,'BlendFunction',GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA);


%get screen size
screenRes = Screen('Resolution',screenNum);
Pstruct = getParamStruct;

% the following give exactly the same result. The tan(1) formula is more intuitive.
% pxDeg = 2*pi/360*Mstate.screenDist*screenRes.width/Mstate.screenXcm;  % pixels per degree
pxDeg = screenRes.width/Mstate.screenXcm * Mstate.screenDist * tan(deg2rad(1));

c=Pstruct.contrast/100;
fore_col = round(255*[Pstruct.fore_r Pstruct.fore_g Pstruct.fore_b]);
if c==0
    fore_col=Pstruct.background;
end

load([Pstruct.stimpath '/stim/stimParams.mat']);

if Pstruct.stimnr == 1
    cPts = [0.5 2.5; 0.5 2.5; -0.5 2.5; -0.5 2.5; -0.5 -2.5; -0.5 -2.5; 0.5 -2.5; 0.5 -2.5]/3;
else 
    stim = stimuli{Pstruct.stimnr};
    cPts = [stim.cPts(:,1) -stim.cPts(:,2)];
end

cPts = movePts(cPts,Pstruct.x_pos,Pstruct.y_pos,pxDeg*Pstruct.xysize,Pstruct.ori); 

concatenatedSplines = drawSpline(cPts,200);

Screen(screenPTROff2, 'FillRect', Pstruct.background);
Screen('FillPoly',screenPTROff2,fore_col, concatenatedSplines);
