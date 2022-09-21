function playgrating_Ramp

global Mstate screenPTR screenNum loopTrial

global Gtxtr TDim daq  %Created in makeGratingTexture

global Stxtr %Created in makeSyncTexture

Pstruct = getParamStruct;

screenRes = Screen('Resolution',screenNum);
pixpercmX = screenRes.width/Mstate.screenXcm;
pixpercmY = screenRes.height/Mstate.screenYcm;

syncWX = round(pixpercmX*Mstate.syncSize);
syncWY = round(pixpercmY*Mstate.syncSize);

white = WhiteIndex(screenPTR); % pixel value for white
black = BlackIndex(screenPTR); % pixel value for black
gray = (white+black)/2;
amp = white-gray;


    
%The following assumes the screen is curved
xcm = 2*pi*Mstate.screenDist*Pstruct.x_size/360;  %stimulus width in cm
xN = round(xcm*pixpercmX);  %stimulus width in pixels
ycm = 2*pi*Mstate.screenDist*Pstruct.y_size/360;   %stimulus height in cm
yN = round(ycm*pixpercmY);  %stimulus height in pixels
    


%Note: I used to truncate these things to the screen size, but it is not
%needed.  It also messes things up.
xran = [Pstruct.x_pos-floor(xN/2)+1  Pstruct.x_pos+ceil(xN/2)];
yran = [Pstruct.y_pos-floor(yN/2)+1  Pstruct.y_pos+ceil(yN/2)];



Npreframes = ceil(Pstruct.predelay*screenRes.hz);
Npostframes = ceil(Pstruct.postdelay*screenRes.hz);


%%%%
%SyncLoc = [0 screenRes.height-syncWY syncWX-1 screenRes.height-1]';
SyncLoc = [0 0 syncWX-1 syncWY-1]';
SyncPiece = [0 0 syncWX-1 syncWY-1]';
StimLoc = [xran(1) yran(1) xran(2) yran(2)]';
StimPiece = [0 0 TDim(2)-1 TDim(1)-1]';
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
for i = 1:Pstruct.Ncontrast*2-1
    frameoff=(i-1)*TDim(3);
    
    Screen('DrawTextures', screenPTR, [Gtxtr(frameoff+1) Stxtr(1)],[StimPiece SyncPiece],[StimLoc SyncLoc]);
    Screen(screenPTR, 'Flip');
    if loopTrial ~=-1
        digWord = 3;  %toggle 2nd bit to signal stim on
        DaqDOut(daq, 0, digWord);
    end
    for j=2:TDim(3)
        Screen('DrawTextures', screenPTR, [Gtxtr(frameoff+j) Stxtr(2)],[StimPiece SyncPiece],[StimLoc SyncLoc]);
        Screen(screenPTR, 'Flip');
        if loopTrial ~=-1 & j==4
            digWord = 1;  %toggle all to low
            DaqDOut(daq, 0, digWord);
        end
    end
end
if loopTrial ~= -1
    digWord = 1;  %toggle 2nd bit to signal stim off
    DaqDOut(daq, 0, digWord);
end


%%%Play postdelay %%%%
for i = 1:Npostframes-1
    Screen('DrawTexture', screenPTR, Stxtr(1),SyncPiece,SyncLoc);
    Screen(screenPTR, 'Flip');
end
Screen('DrawTexture', screenPTR, Stxtr(2),SyncPiece,SyncLoc);
Screen(screenPTR, 'Flip');
if loopTrial ~= -1
    %digWord = bitxor(digWord,7); %toggle all 3 bits (1st/2nd bits go low, 3rd bit is flipped)
    digWord=0; %stop trigger
    DaqDOut(daq, 0,digWord);
    %pause(1);
    %DaqDOut(daq, 0, 0);  %Make sure 3rd bit finishes low
end

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
Screen('DrawTexture', screenPTR, Stxtr(2),SyncPiece,SyncLoc);  
Screen(screenPTR, 'Flip');

