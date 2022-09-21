function playGAManualMapper
clc;
global screenPTR screenPTROff2 Mstate daq screenNum

configurePstate('GM');
Pstruct = getParamStruct;

% databaseName = 'ram_150422_stim';
% serverAddress = '172.30.6.26';
% conn = database(databaseName,'xper_rw','up2nite','Vendor','MySQL','Server',serverAddress);

symbList = {'stimnr','ori','xysize','foreground','background','addMarker','cellNum','showSpikes','visible','showMarkers'};
valdom{1} = 1:200;
valdom{2} = 0:30:359;
valdom{3} = 0.4:0.3:5;
valdom{4} = de2bi(0:7);
valdom{5} = [0 50 100];
valdom{6} = [0 1];
valdom{7} = 1:200;
valdom{8} = [0 1];
valdom{9} = [0 1];
valdom{10} = [0 1];

state.valId = [1 1 3 7 1 1 1 1 2 2];  %Current index for each value domain
state.symId = 2;  %Current symbol index

updatePstate('stimnr',num2str(valdom{1}(state.valId(1))));
updatePstate('ori',num2str(valdom{2}(state.valId(2))));
updatePstate('xysize',num2str(valdom{3}(state.valId(3))));
updatePstate('fore_r',num2str(valdom{4}(state.valId(4),1)));
updatePstate('fore_g',num2str(valdom{4}(state.valId(4),2)));
updatePstate('fore_b',num2str(valdom{4}(state.valId(4),3)));
updatePstate('background',num2str(valdom{5}(state.valId(5))));

makeGAManualMapper;

markerX = []; markerY = [];
spikeX = []; spikeY = [];
showSpikes = 0;

isVisible = true;
showMarkers = false;

symbol = symbList{state.symId};
val = valdom{state.symId}(state.valId(state.symId));
newtext = [symbol ' ' num2str(val)];
dispMarker = 0;

flashCount = 0;
flashFlag = false;
doFlash = 0;

fixSize = 3;
fixCenter = [0 0];

trialOff = 252;
trialOn = 253;
juice = 255;

dataCurrentStatus = [252 254];
trialStatusChanged = 0;

inferredTrialOnStatus = 0; % 0 = off; 1 = on
inferredTrialCompleteStatus = 0; % 0 = break/fail; 1 = complete
trialCount = 1;

trialStatusChan = 1;
spikeChan = 2;

Screen(screenPTR, 'FillRect', valdom{5}(state.valId(5)));

%%%%%Play whats in the buffer (the stimulus)%%%%%%%%%%
Screen('CopyWindow',screenPTROff2,screenPTR);
Screen(screenPTR,'DrawText','stimnr 1',40,30,255-255*floor(valdom{5}(state.valId(5))/255));
Screen('Flip', screenPTR);

bLast = [0 0 0];
keyIsDown = 0;
keyCode = 1;

while true
    kbInput = KbName(keyCode);
    if iscell(kbInput); kbInput = kbInput{1}; end;
    if keyIsDown && (strcmp(kbInput,'q') || strcmp(kbInput,'BackSpace'))
        break;
    end 
    
    data = DaqDIn(daq, 2, 2);
    fixationOn = ~(trialOn-data(trialStatusChan)) || ~(juice-data(trialStatusChan));
    
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
        end
        
        [mx,my,b] = GetMouse(screenPTR);
        b=b(1:3);
        spikeDetected = ~(255-data(spikeChan));
        if spikeDetected % DaqAIn(daq,8,[0 5]) > 2
            spikeX = [spikeX mx];
            spikeY = [spikeY my];
        end
        
        db = bLast - b; %'1' is a button release

        filepath = [getParamVal('stimpath') '/resp/' Mstate.anim '_' Mstate.unit '_' num2str(valdom{7}(state.valId(7))) '.mat'];
        if exist(filepath,'file')
            load(filepath);
        else
            markerX = []; markerY = []; numMarkerPts = 0;
        end
        
        %%%Case 1: Left Button:  decrease value%%%
        if ~sum(abs([1 0 0]-db))  

            symbol = symbList{state.symId};
            state.valId(state.symId) = state.valId(state.symId) - 1;
            if state.valId(state.symId) == 0
                state.valId(state.symId) = length(valdom{state.symId});
            end
            val = valdom{state.symId}(state.valId(state.symId));
            if strcmp(symbol,'foreground')
                updatePstate('fore_r',num2str(valdom{4}(state.valId(4),1)));
                updatePstate('fore_g',num2str(valdom{4}(state.valId(4),2)));
                updatePstate('fore_b',num2str(valdom{4}(state.valId(4),3)));
            elseif strcmp(symbol,'addMarker')
                numMarkerPts = numMarkerPts + 1;
                fileState{numMarkerPts} = state; %#ok<AGROW,NASGU>
                markerX(numMarkerPts) = mx; %#ok<AGROW>
                markerY(numMarkerPts) = my; %#ok<AGROW>
                save(filepath,'fileState','markerX','markerY','numMarkerPts');

%                     rf.x = x; rf.y = y; 
% 
%                     rf.stim.num = valdom{1}(state.valId(1));
%                     rf.stim.ori = valdom{2}(state.valId(2));
%                     rf.stim.siz = valdom{3}(state.valId(3));
%                     
%                     updateRfInDb(rf,[Mstate.unit '_' Mstate.expt],valdom{7}(state.valId(7)),conn);
            elseif strcmp(symbol,'showSpikes')
                showSpikes = 0;
                numSpikes = 0;
                spikeX = [];
                spikeY = [];
            elseif strcmp(symbol,'cellNum')
            elseif strcmp(symbol,'visible')
                isVisible = ~isVisible;
            elseif strcmp(symbol,'showMarkers')
                showMarkers = ~showMarkers;
            else
                updatePstate(symbol,num2str(val));
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
            state.valId(state.symId) = state.valId(state.symId) + 1;
            if state.valId(state.symId) > length(valdom{state.symId})
                state.valId(state.symId) = 1;
            end

            val = valdom{state.symId}(state.valId(state.symId));
            if strcmp(symbol,'foreground')
                updatePstate('fore_r',num2str(valdom{4}(state.valId(4),1)));
                updatePstate('fore_g',num2str(valdom{4}(state.valId(4),2)));
                updatePstate('fore_b',num2str(valdom{4}(state.valId(4),3)));
            elseif strcmp(symbol,'addMarker')
            elseif strcmp(symbol,'showSpikes')  
                numSpikes = 0;
                spikeX = [];
                spikeY = [];
                showSpikes = 1;
            elseif strcmp(symbol,'cellNum')
            elseif strcmp(symbol,'visible')
                isVisible = ~isVisible;
            elseif strcmp(symbol,'showMarkers')
                showMarkers = ~showMarkers;
            else
                updatePstate(symbol,num2str(val));
            end
        end
        updatePstate('x_pos',num2str(mx));
        updatePstate('y_pos',num2str(my));
        
        newtext = [symbol ' ' num2str(val)];
        textColor = 255-255*floor(valdom{5}(state.valId(5))/255);
        
        makeGAManualMapper; 
        
        screenRes = Screen('Resolution',screenNum);
        pixpermmX = screenRes.width/(Mstate.screenXcm*10);
        pixpermmY = screenRes.height/(Mstate.screenYcm*10);
        
        if isVisible
            Screen('CopyWindow',screenPTROff2,screenPTR);
        end
        
        Screen(screenPTR,'DrawText',newtext,40,30,textColor);
        xypos = ['x ' num2str(rad2deg(atan((mx-800)/4/525))) '; y ' num2str(rad2deg(atan((my-600)/4/525)))];
        Screen(screenPTR,'DrawText',xypos,40,55,textColor);
        Mstate.refresh_rate = 1/Screen('GetFlipInterval', screenPTR);

        fixWidth = round(pixpermmX*fixSize);
        fixHeight = round(pixpermmY*fixSize);

        fixLoc = [(screenRes.width+fixCenter(1)-fixWidth)/2 (screenRes.height+fixCenter(2)-fixHeight)/2 ...
                    (screenRes.width+fixCenter(1)+fixWidth)/2 (screenRes.height+fixCenter(2)+fixHeight)/2 ];
        fixPiece = [(screenRes.width+fixCenter(1)-fixWidth)/2 (screenRes.height+fixCenter(2)-fixHeight)/2 ...
                    (screenRes.width+fixCenter(1)+fixWidth)/2 (screenRes.height+fixCenter(2)+fixHeight)/2 ];
        fixColor = zeros(fixHeight,fixWidth,3);
        fixColor(:,:,1:2) = 255;
                
                
        texPointer = Screen(screenPTR, 'MakeTexture', fixColor);
        
        Screen('DrawTexture', screenPTR, texPointer,fixPiece,fixLoc);
        
        if showSpikes
            for ii = 1:length(spikeX)
                spikeBoxWidth = round(pixpermmX*2);
                spikeBoxHeight = round(pixpermmY*2);

                spikeLoc = [spikeX(ii)-(spikeBoxWidth/2) spikeY(ii)-(spikeBoxHeight/2) spikeX(ii)+(spikeBoxWidth/2) spikeY(ii)+(spikeBoxHeight/2)];
                spikePiece = [spikeX(ii)-(spikeBoxWidth/2) spikeY(ii)-(spikeBoxHeight/2) spikeX(ii)+(spikeBoxWidth/2) spikeY(ii)+(spikeBoxHeight/2)];
                spikeColor = zeros(spikeBoxHeight,spikeBoxWidth,3);
                spikeColor(:,:,3) = 255;

                texPointer = Screen(screenPTR, 'MakeTexture', spikeColor);

                Screen('DrawTexture', screenPTR, texPointer,spikePiece,spikeLoc);
            end
        end
        
        if showMarkers
            for ii = 1:length(markerX)
                markerWidth = round(pixpermmX*1);
                markerHeight = round(pixpermmY*1);

                markerLoc = [markerX(ii)-(markerWidth/2) markerY(ii)-(markerHeight/2) markerX(ii)+(markerWidth/2) markerY(ii)+(markerHeight/2)];
                markerPiece = [markerX(ii)-(markerWidth/2) markerY(ii)-(markerHeight/2) markerX(ii)+(markerWidth/2) markerY(ii)+(markerHeight/2)];
                markerColor = zeros(markerHeight,markerWidth,3);
                markerColor(:,:,1) = 255;
                
                texPointer = Screen(screenPTR, 'MakeTexture', markerColor);

                Screen('DrawTexture', screenPTR, texPointer,markerPiece,markerLoc);
            end
        end
        
        Screen('Flip', screenPTR);
        
        bLast = b;
    else
        Screen(screenPTR, 'FillRect', valdom{5}(state.valId(5)))
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
    end
    
    % symbList = {'stimnr','ori','xysize','foreground','background',
    % 'addMarker','cellNum','showSpikes','visible','showMarkers'};
    [keyIsDown,~, keyCode, ~] = KbCheck(-1);
    if ~iscell(KbName(keyCode))
        if strcmp(KbName(keyCode),'m') || strcmp(KbName(keyCode),'KP_Home')
            state.symId = 10; % show/hide markers
        elseif strcmp(KbName(keyCode),'s') || strcmp(KbName(keyCode),'KP_Up')
            state.symId = 1; % stim
        elseif strcmp(KbName(keyCode),'f') || strcmp(KbName(keyCode),'KP_Prior')
            state.symId = 4; % fore color
        elseif strcmp(KbName(keyCode),'v') || strcmp(KbName(keyCode),'KP_Left')
            state.symId = 9; % visible
        elseif strcmp(KbName(keyCode),'o') || strcmp(KbName(keyCode),'KP_Begin')
            state.symId = 2; % ori
        elseif strcmp(KbName(keyCode),'z') || strcmp(KbName(keyCode),'KP_Right')
            state.symId = 3; % size
        end
    end
    symbol = symbList{state.symId};
    val = valdom{state.symId}(state.valId(state.symId));
    
    % KP_Begin, KP_Right, KP_End, KP_Down, KP_Next, KP_Insert, KP_Delete
end

Screen(screenPTR, 'FillRect', Pstruct.background)
Screen(screenPTR, 'Flip');

Screen('Close')  %Get rid of all textures/offscreen windows

