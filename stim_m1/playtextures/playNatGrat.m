function playNatGrat

global Mstate screenPTR screenNum loopTrial

global Gtxtr daq  %Created in makeGratingTexture

global Stxtr %Created in makeSyncTexture

Pstruct = getParamStruct;

%get stimulus size
screenRes = Screen('Resolution',screenNum);
pixpercmX = screenRes.width/Mstate.screenXcm;
pixpercmY = screenRes.height/Mstate.screenYcm;

syncWX = round(pixpercmX*Mstate.syncSize);
syncWY = round(pixpercmY*Mstate.syncSize);



xran = [Pstruct.x_pos-Pstruct.x_px/2+1  Pstruct.x_pos+Pstruct.x_px/2];
yran = [Pstruct.y_pos-Pstruct.y_px/2+1  Pstruct.y_pos+Pstruct.x_px/2];


Npreframes = ceil(Pstruct.predelay*screenRes.hz);
Nstimframes = ceil(Pstruct.stim_time*screenRes.hz);
Npostframes = ceil(Pstruct.postdelay*screenRes.hz);

%%%%
%SyncLoc = [0 screenRes.height-syncWY syncWX-1 screenRes.height-1]';
SyncLoc = [0 0 syncWX-1 syncWY-1]';
SyncPiece = [0 0 syncWX-1 syncWY-1]';
StimLoc = [xran(1) yran(1) xran(2) yran(2)]';
StimPiece = [0 0 Pstruct.x_px-1 Pstruct.y_px-1]';
%%%%



Screen(screenPTR, 'FillRect', Pstruct.background)

%Wake up the daq:
DaqDOut(daq, 0, 0); %I do this at the beginning because it improves timing on the first call to daq below

%%%Play predelay %%%%
Screen('DrawTexture', screenPTR, Stxtr(1),SyncPiece,SyncLoc);
Screen(screenPTR, 'Flip');
if loopTrial ~= -1
    digWord = 1;  %Make 1st bit high
    DaqDOut(daq, 0, digWord);
end
for i = 2:Npreframes
    Screen('DrawTexture', screenPTR, Stxtr(2),SyncPiece,SyncLoc);
    Screen(screenPTR, 'Flip');
end

%%%%%Play whats in the buffer (the stimulus)%%%%%%%%%%
Screen('DrawTextures', screenPTR, [Gtxtr Stxtr(1)],[StimPiece SyncPiece],[StimLoc SyncLoc]);
%Screen('DrawTexture', screenPTR, Gtxtr,[],[100 100 600 600]);
Screen(screenPTR, 'Flip');
if loopTrial ~= -1
    digWord = 3;  %toggle 2nd bit to signal stim on
    DaqDOut(daq, 0, digWord);
end
for i=2:Nstimframes
    Screen('DrawTextures', screenPTR, [Gtxtr Stxtr(1)],[StimPiece SyncPiece],[StimLoc SyncLoc]);
    %Screen('DrawTexture', screenPTR, Gtxtr,[],[100 100 600 600]);
    Screen(screenPTR, 'Flip');
end
if loopTrial ~= -1
    digWord = 1;  %toggle 2nd bit to signal stim off
    DaqDOut(daq, 0, digWord);
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

