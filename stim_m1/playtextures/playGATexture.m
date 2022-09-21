function playGATexture

global Mstate screenPTR screenPTROff2 screenNum loopTrial

global Gtxtr daq  %Created in makeGratingTexture

global Stxtr %Created in makeSyncTexture

global vSyncState %ventilator sync


Pstruct = getParamStruct;

%get stimulus size
screenRes = Screen('Resolution',screenNum);
pixpercmX = screenRes.width/Mstate.screenXcm;
pixpercmY = screenRes.height/Mstate.screenYcm;

syncWX = round(pixpercmX*Mstate.syncSize);
syncWY = round(pixpercmY*Mstate.syncSize);


%in all of the code, we treat the screen as if it is round. this means that
%a stimulus of size x deg ends up having a size in cm of 2pi/360*x deg*monitor
%distance (this is simply the formula for the length of an arc); then
%transform from cm to pixels

%xcm = 2*pi*Mstate.screenDist*Pstruct.x_size/360;  %stimulus width in cm
%xN = round(xcm*pixpercmX);  %stimulus width in pixels
%ycm = 2*pi*Mstate.screenDist*Pstruct.y_size/360;   %stimulus height in cm
%yN = round(ycm*pixpercmY);  %stimulus height in pixels


%xran = [Pstruct.x_pos-floor(xN/2)+1  Pstruct.x_pos+ceil(xN/2)];
%yran = [Pstruct.y_pos-floor(yN/2)+1  Pstruct.y_pos+ceil(yN/2)];

%xran = [Pstruct.x_pos-floor(IDim(2)*Pstruct.scale/2)+1  Pstruct.x_pos+ceil(IDim(2)*Pstruct.scale/2)];
%yran = [Pstruct.y_pos-floor(IDim(1)*Pstruct.scale/2)+1  Pstruct.y_pos+ceil(IDim(1)*Pstruct.scale/2)];


Npreframes = ceil(Pstruct.predelay*screenRes.hz);
Nstimframes = ceil(Pstruct.stim_time*screenRes.hz);
Npostframes = ceil(Pstruct.postdelay*screenRes.hz);

%%%%
%SyncLoc = [0 screenRes.height-syncWY syncWX-1 screenRes.height-1]';
SyncLoc = [0 0 syncWX-1 syncWY-1]';
SyncPiece = [0 0 syncWX-1 syncWY-1]';
%StimLoc = [xran(1) yran(1) xran(2) yran(2)]';
%StimPiece = [0 0 IDim(2)-1 IDim(1)-1]';
%%%%

%disp(StimLoc)


Screen(screenPTR, 'FillRect', Pstruct.background)

%Wake up the daq:
DaqDOut(daq, 0, 0); %I do this at the beginning because it improves timing on the first call to daq below

%%%Play predelay %%%%
Screen('DrawTexture', screenPTR, Stxtr(1),SyncPiece,SyncLoc);
Screen(screenPTR, 'Flip');
if loopTrial ~= -1
    digWord = 1;  %Make 1st bit high
    DaqDOut(daq, 0, digWord);
    %stop ventilator
    if vSyncState==1
        DaqDOut(daq,1,1);
    end
end
for i = 2:Npreframes
    Screen('DrawTexture', screenPTR, Stxtr(2),SyncPiece,SyncLoc);
    Screen(screenPTR, 'Flip');
end

%%%%%Play whats in the buffer (the stimulus)%%%%%%%%%%
Screen('CopyWindow',screenPTROff2,screenPTR);
Screen('DrawTextures', screenPTR, Stxtr(1),SyncPiece,SyncLoc);
%Screen('DrawTexture', screenPTR, Gtxtr,[],[100 100 600 600]);
Screen(screenPTR, 'Flip');
if loopTrial ~= -1
    digWord = 3;  %toggle 2nd bit to signal stim on
    DaqDOut(daq, 0, digWord);
end
for i=2:Nstimframes
    Screen('CopyWindow',screenPTROff2,screenPTR);
    Screen('DrawTextures', screenPTR, Stxtr(1),SyncPiece,SyncLoc);
    %Screen('DrawTextures', screenPTR, [Gtxtr Stxtr(1)],[StimPiece StimPiece],[StimLoc SyncLoc]);
    %Screen('DrawTexture', screenPTR, Gtxtr,[],[100 100 600 600]);
    Screen(screenPTR, 'Flip');
end
if loopTrial ~= -1
    digWord = 1;  %toggle 2nd bit to signal stim off
    DaqDOut(daq, 0, digWord);
    %start ventilator
    if vSyncState==1
        DaqDOut(daq,1,0);
    end
end

%%%Play postdelay %%%%
for i = 1:Npostframes-1
    Screen('DrawTexture', screenPTR, Stxtr(2),SyncPiece,SyncLoc);
    Screen(screenPTR, 'Flip');
end
Screen('DrawTexture', screenPTR, Stxtr(1),SyncPiece,SyncLoc);
Screen(screenPTR, 'Flip');
if loopTrial ~= -1
    DaqDOut(daq, 0, 0);  %Make sure 3rd bit finishes low
end

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
Screen('DrawTexture', screenPTR, Stxtr(2),SyncPiece,SyncLoc);  
Screen(screenPTR, 'Flip');

