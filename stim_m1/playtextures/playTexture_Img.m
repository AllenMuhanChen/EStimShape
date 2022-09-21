function playTexture_Img

global  screenPTR Mstate daq screenNum
global Gtxtr IDim

configurePstate('IM');

symbList = {'imgbase1','imgbase2','imgnr','size','visible'};
valdom{1} = 1;
valdom{2} = 1:4;
valdom{3} = 0:199;
valdom{4} = 3:10;
valdom{5} = 0:1;

imgbase1_str={'medialAxis'};
imgbase2_str{1}={'SHADE','SPEC','2D','SCRAMBLE'};

%set starting value and symbol 
state.valId = [1 1 1 1 2];  %Current index for each value domain
state.symId = 1;  %Current symbol index

%update the parameters - we only need imgbase and imgnr to make the image
updatePstate('imgbase1',imgbase1_str{valdom{1}(state.valId(1))});
updatePstate('imgbase2',imgbase2_str{valdom{1}(state.valId(1))}{valdom{2}(state.valId(2))});
updatePstate('imgnr',num2str(valdom{3}(state.valId(3))));
updatePstate('size',num2str(valdom{4}(state.valId(4))));

%initialize texture
makeTexture_Img %this populates Gtxtr and IDim

screenRes = Screen('Resolution',screenNum);
pixpermmX = screenRes.width/(Mstate.screenXcm*10);
pixpermmY = screenRes.height/(Mstate.screenYcm*10);

Mstate.refresh_rate = 1/Screen('GetFlipInterval', screenPTR);

fixSize = 3; % mm
fixCenter = [0 0];
fixWidth = round(pixpermmX*fixSize);
fixHeight = round(pixpermmY*fixSize);

fixLoc = [(screenRes.width+fixCenter(1)-fixWidth)/2 (screenRes.height+fixCenter(2)-fixHeight)/2 ...
            (screenRes.width+fixCenter(1)+fixWidth)/2 (screenRes.height+fixCenter(2)+fixHeight)/2 ];
fixPiece = [(screenRes.width+fixCenter(1)-fixWidth)/2 (screenRes.height+fixCenter(2)-fixHeight)/2 ...
            (screenRes.width+fixCenter(1)+fixWidth)/2 (screenRes.height+fixCenter(2)+fixHeight)/2 ];
fixColor = zeros(fixHeight,fixWidth,3);
fixColor(:,:,1:2) = 255;

isVisible = true;

trialOff = 252;
trialOn = 253;
juice = 255;

dataCurrentStatus = [252 254];
trialStatusChanged = 0;

inferredTrialOnStatus = 0; % 0 = off; 1 = on
inferredTrialCompleteStatus = 0; % 0 = break/fail; 1 = complete
trialCount = 1;

trialStatusChan = 1;

%initialize text
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
        db = bLast - b; %'1' is a button release

        %%%Case 1: Left Button:  decrease value%%%
        if ~sum(abs([1 0 0]-db))  

            symbol = symbList{state.symId};
            state.valId(state.symId) = state.valId(state.symId) - 1;
            if state.valId(state.symId) == 0
                state.valId(state.symId) = length(valdom{state.symId});
            end
            val = valdom{state.symId}(state.valId(state.symId));
            
            %in these cases we need to regenerate the stimulus
            if strcmp(symbol,'imgbase1')
                updatePstate('imgbase1',imgbase1_str{val});
            elseif strcmp(symbol,'imgbase2')                
                updatePstate('imgbase2',imgbase2_str{valdom{1}(state.valId(1))}{val});
            elseif strcmp(symbol,'visible')
                isVisible = ~isVisible;
            else
                updatePstate(symbol,num2str(val)); 
            end

        end

        %%%Case 2: Middle Button:  change parameter%%%
        if ~sum(abs([0 1 0]-db))

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

            %in these cases we need to regenerate the stimulus
            if strcmp(symbol,'imgbase1')
                updatePstate('imgbase1',imgbase1_str{val});
            elseif strcmp(symbol,'imgbase2')
                updatePstate('imgbase2',imgbase2_str{valdom{1}(state.valId(1))}{val});
            elseif strcmp(symbol,'visible')
                isVisible = ~isVisible;
            else
                updatePstate(symbol,num2str(val)); 
            end
        end
        updatePstate('x_pos',num2str(mx));
        updatePstate('y_pos',num2str(my));

        newtext = [symbol ' ' num2str(val)];
        textColor = 0;
        
        makeTexture_Img;

        if isVisible
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
        xypos = ['x ' num2str(rad2deg(atan((mx-800)/4/616))) '; y ' num2str(rad2deg(atan((my-600)/4/616)))];
%         xypos = ['x ' num2str(mx) '; y ' num2str(my)];
        Screen(screenPTR,'DrawText',xypos,40,55,textColor);
        Mstate.refresh_rate = 1/Screen('GetFlipInterval', screenPTR);

        texPointer = Screen(screenPTR, 'MakeTexture', fixColor);
        Screen('DrawTexture', screenPTR, texPointer,fixPiece,fixLoc);
        
        Screen('Flip', screenPTR);
        
        bLast = b;
    else
        Screen(screenPTR, 'FillRect',127)
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
    
    % symbList = {'imgbase1','imgbase2','imgnr','size','visible'};
    [keyIsDown,~, keyCode, ~] = KbCheck(-1);
    if ~iscell(KbName(keyCode))
        if  strcmp(KbName(keyCode),'s') || strcmp(KbName(keyCode),'KP_Up')
            state.symId = 3; % stim
        elseif strcmp(KbName(keyCode),'b') || strcmp(KbName(keyCode),'KP_Prior')
            state.symId = 2; % base2
        elseif strcmp(KbName(keyCode),'v') || strcmp(KbName(keyCode),'KP_Left')
            state.symId = 5; % visible
        elseif strcmp(KbName(keyCode),'z') || strcmp(KbName(keyCode),'KP_Right')
            state.symId = 4; % size
        end
    end
    symbol = symbList{state.symId};
    val = valdom{state.symId}(state.valId(state.symId));
    
    % KP_Begin, KP_Right, KP_End, KP_Down, KP_Next, KP_Insert, KP_Delete
end

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
Screen(screenPTR, 'FillRect', 0.5)
Screen(screenPTR, 'Flip');

Screen('Close')  %Get rid of all textures/offscreen windows
