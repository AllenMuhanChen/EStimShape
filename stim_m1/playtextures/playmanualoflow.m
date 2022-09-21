function playmanualoflow

global Mstate screenPTR screenNum 

global DotFrame  %Created in makeOpticFlow

Pstruct = getParamStruct;

screenRes = Screen('Resolution',screenNum);
pixpercmX = screenRes.width/Mstate.screenXcm;
pixpercmY = screenRes.height/Mstate.screenYcm;


%%%%%%%%%%%%%%%%%%

symbList = {'stimType','stimDir','dotDensity','sizeDots','speedDots','stimRadius'};
valdom{1} = 0:4; %stimType
valdom{2} = [-1 1]; %stimDir
valdom{3} = logspace(log10(5),log10(500),10); %dotDensity
valdom{4} = logspace(log10(.2),log10(2),10); %dotSize
valdom{5} = logspace(log10(.5),log10(20),20); %speed
valdom{6} = logspace(log10(1),log10(60),20); %stimRadius

state.valId = [1 2 7 1 13 9];  %Current index for each value domain
state.symId = 1;  %Current symbol index
%%%%%%%%%%%%%%%
%%%%%%%%%%%%%%%

%initialize the texture
for i = 1:length(valdom)
    symbol = symbList{i};
    val = valdom{i}(state.valId(i));
    updatePstate(symbol,num2str(val));
end
%make sure we use round dots for this
updatePstate('dotType',num2str(1));
%also make sure the movie is long enough
updatePstate('stim_time',num2str(10));


makeOpticFlow

symbol = symbList{state.symId};
val = valdom{state.symId}(state.valId(state.symId));
newtext = [symbol ' ' num2str(val)];


Screen(screenPTR, 'FillRect', 0)

%%%%%Play whats in the buffer (the stimulus)%%%%%%%%%%

%Screen(screenPTR,'DrawText',newtext,40,30,255);
%screen('Flip', screenPTR);

TextrIdx = 1;
bLast = [0 0 0];
keyIsDown = 0;
while ~keyIsDown
    
    [mx,my,b] = GetMouse(screenPTR);
    
    b=b(1:3);
    
    db = bLast - b; %'1' is a button release
           
    
    %%%Case 1: Left Button:  decrease value%%%
    if ~sum(abs([1 0 0]-db))  
        
        symbol = symbList{state.symId};
        if state.valId(state.symId) > 1
            state.valId(state.symId) = state.valId(state.symId) - 1;
        end       
        
        val = valdom{state.symId}(state.valId(state.symId));
       
        updatePstate(symbol,num2str(val));
        if ~strcmp(symbol,'sizeDots')
            makeOpticFlow
        end
        
        newtext = [symbol ' ' num2str(val)];
        
        %Screen(screenPTR,'DrawText',newtext,40,30,255);
        %Screen('Flip', screenPTR);
    end
    
    %%%Case 2: Middle Button:  change parameter%%%
    if ~sum(abs([0 0 1]-db))  % [0 0 1] is the scroll bar in the middle
        
        state.symId = state.symId+1; %update the symbol
        if state.symId > length(symbList)
            state.symId = 1; %unwrap
        end
        symbol = symbList{state.symId};
        val = valdom{state.symId}(state.valId(state.symId));
        
        newtext = [symbol ' ' num2str(val)];
        
        %Screen(screenPTR,'DrawText',newtext,40,30,255);
        %Screen('Flip', screenPTR);
    end
    
    %%%Case 3: Right Button: increase value%%%
    if ~sum(abs([0 1 0]-db))  %  [0 1 0]  is right click
        
        symbol = symbList{state.symId};
        if state.valId(state.symId) < length(valdom{state.symId})
            state.valId(state.symId) = state.valId(state.symId) + 1;
        end
      
        val = valdom{state.symId}(state.valId(state.symId));        
        
        updatePstate(symbol,num2str(val));
        if ~strcmp(symbol,'sizeDots')
            makeOpticFlow
        end
       
        
        newtext = [symbol ' ' num2str(val)];
        
        %Screen(screenPTR,'DrawText',newtext,40,30,255);
        %Screen('Flip', screenPTR);
    end
    
    disp('test')
    
    TextrIdx = rem(TextrIdx,length(DotFrame))+1;
    
    sizeDots=valdom{4}(state.valId(4));
    sizeDotsCm=sizeDots*2*pi/360*Mstate.screenDist;
    sizeDotsPx=round(sizeDotsCm*pixpercmX);
    
    Screen('DrawDots', screenPTR, DotFrame{TextrIdx}, sizeDotsPx, [255 255 255],...
        [mx my],1);
     
    Screen(screenPTR,'DrawText',newtext,40,30,255);
    xypos = ['x ' num2str(mx) '; y ' num2str(my)];
    Screen(screenPTR,'DrawText',xypos,40,55,255);
    Screen('Flip', screenPTR);
    
    bLast = b;
    
    keyIsDown = KbCheck(-1);
    
end



%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
Screen(screenPTR, 'FillRect', Pstruct.background)
Screen(screenPTR, 'Flip');

Screen('Close')  %Get rid of all textures/offscreen windows

