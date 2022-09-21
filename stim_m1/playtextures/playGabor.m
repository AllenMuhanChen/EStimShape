function playGabor
clc;
global  screenPTR Mstate daq screenNum
global Gtxtr IDim

configurePstate('IMGab');

symbList = {'ori','sw','phase','siz','cont','aRatio','col1','col2','place','clear','visible'};
valdom{1}  = 0:45:359;
valdom{2}  = 0.5:0.5:4;
valdom{3}  = [0 90];
valdom{4}  = 2:2:10;
valdom{5}  = 0.5:0.25:1;
valdom{6}  = [0.5 1 2];
valdom{7}  = 1:8;
valdom{8}  = 1:8;
valdom{9}  = 1;
valdom{10} = 1;
valdom{11} = [0 1];

%set starting value and symbol 
state.valId = [1 3 1 2 3 2 1 8 1 1 2];  %Current index for each value domain
state.symId = 1;  %Current symbol index

%update the parameters - we only need imgbase and imgnr to make the image
for ii=1:8
    updatePstate(symbList{ii},num2str(valdom{ii}(state.valId(ii))));
end

%initialize texture
makeTexture_Gabor %this populates Gtxtr and IDim

% to cache images so as to not keep regenerate on every refresh
imgChange = 0;

% static images
placedN = 0;
placed = [];

% daq read ids
trialOff = 252;
trialOn = 253;
juice = 255;

dataCurrentStatus = [252 254];

inferredTrialOnStatus = 0; % 0 = off; 1 = on
inferredTrialCompleteStatus = 0; % 0 = break/fail; 1 = complete
trialCount = 1;

trialStatusChan = 1;

%initialize text
textColor = 255;
symbol = symbList{state.symId};
val = valdom{state.symId}(state.valId(state.symId));
newtext = [symbol ' ' num2str(val)];

%initialize screen
Screen(screenPTR, 'FillRect', 127)
Screen(screenPTR,'DrawText',newtext,40,30,1);
Screen('Flip', screenPTR);

bLast = [0 0 0];
keyIsDown = 0;
keyCode = 1;

screenRes = Screen('Resolution',screenNum);
pixpermmX = screenRes.width/(Mstate.screenXcm*10);
pixpermmY = screenRes.height/(Mstate.screenYcm*10);

% fixation
fixSize = 1.2;
fixCenter = [0 0];

fixWidth = round(pixpermmX*fixSize);
fixHeight = round(pixpermmY*fixSize);

fixLoc = [(screenRes.width+fixCenter(1)-fixWidth)/2 (screenRes.height+fixCenter(2)-fixHeight)/2 ...
            (screenRes.width+fixCenter(1)+fixWidth)/2 (screenRes.height+fixCenter(2)+fixHeight)/2 ];
fixPiece = [(screenRes.width+fixCenter(1)-fixWidth)/2 (screenRes.height+fixCenter(2)-fixHeight)/2 ...
            (screenRes.width+fixCenter(1)+fixWidth)/2 (screenRes.height+fixCenter(2)+fixHeight)/2 ];
fixColor = zeros(fixHeight,fixWidth,3);
fixColor(:,:,1:2) = 200;

while true
    kbInput = KbName(keyCode);
    if iscell(kbInput); kbInput = kbInput{1}; end;
    if keyIsDown && (strcmp(kbInput,'q') || strcmp(kbInput,'BackSpace'))
        break;
    end 
    
    data = DaqDIn(daq, 2, 2);
    if numel(data) == 0
        continue;
    end
    fixationOn = ~(trialOn-data(trialStatusChan)) || ~(juice-data(trialStatusChan));
    % fixationOn = true;
    
    if data(trialStatusChan) ~= dataCurrentStatus(trialStatusChan)
        trialStatusChanged = 1;
    else
        trialStatusChanged = 0;
    end
    dataCurrentStatus = data;
    
    if fixationOn
        if trialStatusChanged && ~inferredTrialOnStatus(trialCount) % if trial was previously off
            disp([num2str(trialCount) ': trial started']);
            inferredTrialOnStatus(trialCount) = 1;
            
            fixColor = zeros(fixHeight,fixWidth,3);
            fixColor(:,:,1:2) = 200;
        end
        
        [mx,my,b] = GetMouse(screenPTR);
        b=b(1:3);
        db = bLast - b; %'1' is a button release

        %%%Case 1: Left Button:  decrease value%%%
        if ~sum(abs([1 0 0]-db))  
            symbol = symbList{state.symId};
            if strcmp(symbol,'place')
                placedN = placedN + 1;
                placed(placedN).dim = IDim;
                placed(placedN).pos = [mx my];
                placed(placedN).siz = valdom{4}(state.valId(4));
                
                [img,~,al]=imread('/stimulator_slave/makeTextures/utils/temp_img.png');
                img=double(cat(3,img,al));
                placed(placedN).img=img;
            elseif strcmp(symbol,'clear')
                placed = [];
                placedN = 0;
            else
                state.valId(state.symId) = state.valId(state.symId) - 1;
                if state.valId(state.symId) == 0
                    state.valId(state.symId) = length(valdom{state.symId});
                end
                val = valdom{state.symId}(state.valId(state.symId));
                if ~strcmp(symbol,'visible')
                    updatePstate(symbol,num2str(val));
                    imgChange = 1;
                end
            end
        end

        %%%Case 2: Middle Button:  change parameter%%%
        if ~sum(abs([0 1 0]-db))  % [0 0 1] is the scroll bar in the middle
            state.symId = state.symId+1; %update the symbol
            if state.symId > length(symbList)
                state.symId = 1; %unwrap
            end
            symbol = symbList{state.symId};
            val = valdom{state.symId}(state.valId(state.symId));
        end

        %%%Case 3: Right Button: increase value%%%
        if ~sum(abs([0 0 1]-db))  %  [0 1 0]  is right click
            symbol = symbList{state.symId};
            if strcmp(symbol,'place')
                placedN = placedN + 1;
                placed(placedN).dim = IDim;
                placed(placedN).pos = [mx my];
                placed(placedN).siz = valdom{4}(state.valId(4));
                
                [img,~,al]=imread('/stimulator_slave/makeTextures/utils/temp_img.png');
                img=double(cat(3,img,al));
                placed(placedN).img=img;
            elseif strcmp(symbol,'clear')
                placed = [];
                placedN = 0;
            else
                state.valId(state.symId) = state.valId(state.symId) + 1;
                if state.valId(state.symId) > length(valdom{state.symId})
                    state.valId(state.symId) = 1;
                end
                val = valdom{state.symId}(state.valId(state.symId));
                if ~strcmp(symbol,'visible')
                    updatePstate(symbol,num2str(val));
                    imgChange = 1;
                end
            end
        end
        updatePstate('x_pos',num2str(mx));
        updatePstate('y_pos',num2str(my));
        
        newtext = [symbol ' ' num2str(val)];
        
        if imgChange
            makeTexture_Gabor; 
            imgChange = 0;
        end
        
        if valdom{11}(state.valId(11))
            for ii=1:placedN
                GtxtrP(ii) = Screen(screenPTR, 'MakeTexture', placed(ii).img);

                xcm = Mstate.screenDist * tan(deg2rad(placed(ii).siz));
                xN = round(xcm*pixpermmX*10);  %stimulus width in pixels
                yN = round((xN/placed(ii).dim(1)) * placed(ii).dim(2));

                xran = [placed(ii).pos(1)-floor(xN/2)+1  placed(ii).pos(1)+ceil(xN/2)];
                yran = [placed(ii).pos(2)-floor(yN/2)+1  placed(ii).pos(2)+ceil(yN/2)];
                StimLoc = [xran(1) yran(1) xran(2) yran(2)]';
                StimPiece = [0 0 placed(ii).dim(1)-1 placed(ii).dim(2)-1]';
                Screen('DrawTexture', screenPTR, GtxtrP(ii),StimPiece,StimLoc);
            end

            xcm = Mstate.screenDist * tan(deg2rad(valdom{4}(state.valId(4))));
            xN = round(xcm*pixpermmX*10);  %stimulus width in pixels
            yN = round((xN/IDim(1)) * IDim(2));

            xran = [mx-floor(xN/2)+1  mx+ceil(xN/2)];
            yran = [my-floor(yN/2)+1  my+ceil(yN/2)];
            StimLoc = [xran(1) yran(1) xran(2) yran(2)]';
            StimPiece = [0 0 IDim(1)-1 IDim(2)-1]';
            Screen('DrawTexture', screenPTR, Gtxtr,StimPiece,StimLoc);
        end
        
        Screen(screenPTR,'DrawText',newtext,40,30,textColor);
        xypos = ['x ' num2str(rad2deg(atan((mx-800)/4/500))) '; y ' num2str(rad2deg(atan((my-600)/4/500)))];
        Screen(screenPTR,'DrawText',xypos,40,55,textColor);
        Mstate.refresh_rate = 1/Screen('GetFlipInterval', screenPTR);
 
        texPointer = Screen(screenPTR, 'MakeTexture', fixColor);
        Screen('DrawTexture', screenPTR, texPointer,fixPiece,fixLoc);

        Screen('Flip', screenPTR);
        
        bLast = b;
    else
        Screen(screenPTR, 'FillRect', 0);
        Screen(screenPTR, 'Flip'); 
    end
    
    if trialStatusChanged && data(trialStatusChan) == trialOff
        if inferredTrialCompleteStatus(trialCount)
            disp([num2str(trialCount) ': trial ended - successful']);
        else
            disp([num2str(trialCount) ': trial ended - break/fail']);
        end
        disp(['Working at ' num2str(round(100*sum(inferredTrialCompleteStatus)/length(inferredTrialCompleteStatus))) '% correct']);
        trialCount = trialCount + 1;
        inferredTrialOnStatus(trialCount) = 0;
        inferredTrialCompleteStatus(trialCount) = 0;
    elseif trialStatusChanged && data(trialStatusChan) == juice
        if inferredTrialCompleteStatus(trialCount)
            disp([num2str(trialCount) ': bonus juice delivered']);
        else
            inferredTrialCompleteStatus(trialCount) = 1;
            disp([num2str(trialCount) ': juice delivered']);
        end
        
        fixColor = zeros(fixHeight,fixWidth,3);
    end
    
    [keyIsDown,~, keyCode, ~] = KbCheck(-1);
    if ~iscell(KbName(keyCode))
        if strcmp(KbName(keyCode),'s') || strcmp(KbName(keyCode),'KP_Up')
            state.symId = 1; % stim
        elseif strcmp(KbName(keyCode),'f') || strcmp(KbName(keyCode),'KP_Prior')
            state.symId = 4; % fore color
        elseif strcmp(KbName(keyCode),'o') || strcmp(KbName(keyCode),'KP_Begin')
            state.symId = 2; % ori
        elseif strcmp(KbName(keyCode),'z') || strcmp(KbName(keyCode),'KP_Right')
            state.symId = 3; % size
        end
    end
    symbol = symbList{state.symId};
    val = valdom{state.symId}(state.valId(state.symId));
end

Screen(screenPTR, 'FillRect', 0.5)
Screen(screenPTR, 'Flip');

Screen('Close')  %Get rid of all textures/offscreen windows

