function playgrating_DualGrater

%This one uses the sequences that were already defined in the make file

global Mstate screenPTRStereo screenNum daq loopTrial

global Gtxtr TDim Mtxtr StimAperture %Created in makeGratingTexture

global Stxtr %Created in makeSyncTexture


P = getParamStruct;

screenRes = Screen('Resolution',screenNum);
pixpercmX = screenRes.width/Mstate.screenXcm;
pixpercmY = screenRes.height/Mstate.screenYcm;

syncWX = round(pixpercmX*Mstate.syncSize);
syncWY = round(pixpercmY*Mstate.syncSize);

white = WhiteIndex(screenPTRStereo); % pixel value for white
black = BlackIndex(screenPTRStereo); % pixel value for black
gray = (white+black)/2;

%The following gives inaccurate spatial frequencies
% xN = 2*Mstate.screenDist*tan(P.x_size/2*pi/180);  %grating width in cm
% xN = round(xN*pixpercmX);  %grating width in pixels
% yN = 2*Mstate.screenDist*tan(P.y_size/2*pi/180);  %grating height in cm
% yN = round(yN*pixpercmY);  %grating height in pixels

%The following assumes the screen is curved
xcm = 2*pi*Mstate.screenDist*P.x_size/360;  %stimulus width in cm
xN = round(xcm*pixpercmX);  %stimulus width in pixels
ycm = 2*pi*Mstate.screenDist*P.y_size/360;   %stimulus height in cm
yN = round(ycm*pixpercmY);  %stimulus height in pixels

CFSxcm = 2*pi*Mstate.screenDist*P.CFSx_size/360;  %stimulus width in cm
CFSxN = round(CFSxcm*pixpercmX);  %stimulus width in pixels
CFSycm = 2*pi*Mstate.screenDist*P.CFSy_size/360;   %stimulus height in cm
CFSyN = round(CFSycm*pixpercmY);  %stimulus height in pixels


%Note: I used to truncate these things to the screen size, but it is not
%needed.  It also messes things up.
xran = [P.x_pos-floor(xN/2)+1  P.x_pos+ceil(xN/2)];
yran = [P.y_pos-floor(yN/2)+1  P.y_pos+ceil(yN/2)];
CFSxstim = [P.x_pos-floor(CFSxN/2)+1  P.x_pos+ceil(CFSxN/2)];
CFSystim = [P.y_pos-floor(CFSyN/2)+1  P.y_pos+ceil(CFSyN/2)];


SyncLoc = [0 0 syncWX-1 syncWY-1]';
SyncPiece = [0 0 syncWX-1 syncWY-1]';
StimLoc = [xran(1) yran(1) xran(2) yran(2)]';
srcrect = [0 0 TDim(1) TDim(2)]';
MaskLoc = [CFSxstim(1) CFSystim(1) CFSxstim(2) CFSystim(2)]';


Npreframes = ceil(P.predelay*screenRes.hz);
Npostframes = ceil(P.postdelay*screenRes.hz);


N_Im = round(P.stim_time*screenRes.hz/P.h_per); %number of images to present
Nstimframes=N_Im*P.h_per;
N_ImMask = ceil(Nstimframes/P.CFSh_per); %number of masks to present



Screen('SelectStereoDrawBuffer', screenPTRStereo, 0);
Screen(screenPTRStereo, 'FillRect', P.background)
Screen('SelectStereoDrawBuffer', screenPTRStereo, 1);
Screen(screenPTRStereo, 'FillRect', P.background)

%Wake up the daq:
DaqDOut(daq, 0, 0); %I do this at the beginning because it improves timing on the first call to daq below

%%%Play predelay %%%%
Screen('SelectStereoDrawBuffer', screenPTRStereo, 0);
Screen('DrawTexture', screenPTRStereo, Stxtr(1),SyncPiece,SyncLoc);
Screen('SelectStereoDrawBuffer', screenPTRStereo, 1);
Screen('DrawTexture', screenPTRStereo, Stxtr(1),SyncPiece,SyncLoc);
Screen(screenPTRStereo, 'Flip');
if loopTrial ~= -1
    digWord = 1;  %Make 1st,2nd,3rd bits high
    DaqDOut(daq, 0, digWord);
end
for i = 2:Npreframes
    Screen('SelectStereoDrawBuffer', screenPTRStereo, 0);
    Screen('DrawTexture', screenPTRStereo, Stxtr(2),SyncPiece,SyncLoc);
    Screen('SelectStereoDrawBuffer', screenPTRStereo, 1);
    Screen('DrawTexture', screenPTRStereo, Stxtr(2),SyncPiece,SyncLoc);
    Screen(screenPTRStereo, 'Flip');
end

%%%%%Play whats in the buffer (the stimulus)%%%%%%%%%%

%Unlike periodic grater, this doesn't produce a digital sync on last frame, just
%the start of each grating.  But this one will always show 'h_per' frames on
%the last grating, regardless of 'stimtime'.


Screen('SelectStereoDrawBuffer', screenPTRStereo, P.CFSstim_mon);
Screen('DrawTextures', screenPTRStereo, [Gtxtr(1) Stxtr(1)],[],[StimLoc SyncLoc]);
Screen('DrawTextures', screenPTRStereo, StimAperture,[],StimLoc);


if P.CFSmask_bit==1
    Screen('SelectStereoDrawBuffer', screenPTRStereo, P.CFSmask_mon);
    Screen('DrawTextures', screenPTRStereo, [Mtxtr(1) Stxtr(1)],[],[MaskLoc SyncLoc]);
end

Screen('SelectStereoDrawBuffer', screenPTRStereo, 1-P.CFSstim_mon);
Screen('DrawTextures', screenPTRStereo, Stxtr(1),[],SyncLoc);


if loopTrial ~= -1
    digWord = 3;  %toggle 2nd bit to signal stim on
    DaqDOut(daq, 0, digWord);
end

countstim=1;
countmask=1;
for i = 2:Nstimframes
    
    if mod(i,P.h_per)==1
        countstim=countstim+1;   
    end
    if mod(i,P.CFSh_per)==1
        countmask=countmask+1;
    end
    
    
    Screen('SelectStereoDrawBuffer', screenPTRStereo, P.CFSstim_mon);
    Screen('DrawTextures', screenPTRStereo, [Gtxtr(countstim) Stxtr(2-rem(countstim,2))],[],[StimLoc SyncLoc]);
    Screen('DrawTextures', screenPTRStereo, StimAperture,[],StimLoc);
    
    if P.CFSmask_bit==1
        Screen('SelectStereoDrawBuffer', screenPTRStereo, P.CFSmask_mon);
        Screen('DrawTextures', screenPTRStereo, Mtxtr(countmask),[],MaskLoc);
    end
    
    Screen('SelectStereoDrawBuffer', screenPTRStereo, 1-P.CFSstim_mon);
    Screen('DrawTextures', screenPTRStereo, Stxtr(2-rem(countstim,2)),[],SyncLoc);
    
    
    Screen(screenPTRStereo, 'Flip');
    
    %if i==1 && loopTrial ~= -1
    if loopTrial ~= -1 && mod(i,P.h_per)==1
        digWord = 3;  %toggle 2nd bit to signal stim on
        DaqDOut(daq, 0, digWord);
    end  
        
    if loopTrial ~=-1 && mod(i,P.h_per)==2
        digWord = 1;  %toggle 2nd bit to signal stim on
        DaqDOut(daq, 0, digWord);
    end
end
if loopTrial ~= -1
    digWord = 1;  %toggle 2nd bit to signal stim on
    DaqDOut(daq, 0, digWord);
end
    

%%%Play postdelay %%%%
for i = 1:Npostframes-1
    Screen('SelectStereoDrawBuffer', screenPTRStereo, 0);
    Screen('DrawTexture', screenPTRStereo, Stxtr(2),SyncPiece,SyncLoc);
    Screen('SelectStereoDrawBuffer', screenPTRStereo, 1);
    Screen('DrawTexture', screenPTRStereo, Stxtr(2),SyncPiece,SyncLoc);
    Screen(screenPTRStereo, 'Flip');
end
Screen('SelectStereoDrawBuffer', screenPTRStereo, 0);
Screen('DrawTexture', screenPTRStereo, Stxtr(1),SyncPiece,SyncLoc);
Screen('SelectStereoDrawBuffer', screenPTRStereo, 1);
Screen('DrawTexture', screenPTRStereo, Stxtr(1),SyncPiece,SyncLoc);
Screen(screenPTRStereo, 'Flip');
%digWord = bitxor(digWord,7); %toggle all 3 bits (1st/2nd bits go low, 3rd bit is flipped)
%DaqDOut(daq, 0,digWord);  

if loopTrial ~= -1
    DaqDOut(daq, 0, 0);  %Make sure 3rd bit finishes low
end

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
Screen('SelectStereoDrawBuffer', screenPTRStereo, 0);
Screen('DrawTexture', screenPTRStereo, Stxtr(2),SyncPiece,SyncLoc);  
Screen('SelectStereoDrawBuffer', screenPTRStereo, 1);
Screen('DrawTexture', screenPTRStereo, Stxtr(2),SyncPiece,SyncLoc);  
Screen(screenPTRStereo, 'Flip');



