function screenconfig

global screenPTR screenNum Mstate screenPTROff screenPTROff2 screenPTRStereo screenRes

%screens=Screen('Screens');
%screenNum=max(screens);

AssertOpenGL;
InitializeMatlabOpenGL;

screenNum=2;

screenRes = Screen('Resolution',screenNum);


%open window for regular drawing
screenPTR = Screen('OpenWindow',screenNum);
% Screen('Preference', 'SkipSyncTests', 1); 
% screenPTR = Screen('OpenWindow', screenNum, [],[],[],[],[],8,[]);
Screen(screenPTR,'BlendFunction',GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA);

%open offscreen window for opengl drawing
screenPTROff=Screen('OpenOffscreenWindow',screenPTR,[128 128 128 255]);
Screen(screenPTROff,'BlendFunction',GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA);

%open offscreen window for GA drawing
screenPTROff2=Screen('OpenOffscreenWindow',screenPTR,[],[],[],[],8);
Screen(screenPTROff2,'BlendFunction',GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA);

%open windows for stereomode
% if length(Screen('Screens')) == 2
%     stereoMode=10; %this is 2 monitors on a mac
%     PsychImaging('PrepareConfiguration');
%     sca
%this is the main screen
%     slaveScreen = 1;
%     Screen('OpenWindow', slaveScreen, BlackIndex(slaveScreen), [], [], [], stereoMode);
%     Screen(screenPTRStereo,'BlendFunction',GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA);
% end



updateMonitor

Screen('PixelSizes',screenPTR)

% pixpercmX = screenRes.width/Mstate.screenXcm;
% pixpercmY = screenRes.height/Mstate.screenYcm;

% syncWX = round(pixpercmX*Mstate.syncSize);
% syncWY = round(pixpercmY*Mstate.syncSize);

Mstate.refresh_rate = 1/Screen('GetFlipInterval', screenPTR);

% %SyncLoc = [0 screenRes.height-syncWY syncWX-1 screenRes.height-1]';
% SyncLoc = [0 0 syncWX-1 syncWY-1]';
% SyncPiece = [0 0 syncWX-1 syncWY-1]';
% 
% %Set the screen
% 
% Screen(screenPTR, 'FillRect', 128)
% Screen(screenPTR, 'Flip');
% 
% wsync = Screen(screenPTR, 'MakeTexture', 0*ones(syncWY,syncWX)); % "low"
% 
% Screen('DrawTexture', screenPTR, wsync,SyncPiece,SyncLoc);
% Screen(screenPTR, 'Flip');


