function playmanualoflow

global Mstate screenPTR screenNum screenPTROff

global Stxtr  %Created in makeangle

Pstruct = getParamStruct;

screenRes = Screen('Resolution',screenNum);
pixpercmX = screenRes.width/Mstate.screenXcm;


%%%%%%%%%%%%%%%%%%

symbList = {'stimori','stimacute','stimsmooth','stimtype','linewidth','radius','background'};
valdom{1} = 0:10:350; %stimori
valdom{2} = 15:15:165; %stimacute
valdom{3} = [0 1]; %stimsmooth
valdom{4} = [0 1 2]; %stimtype
valdom{5} = logspace(log10(1),log10(50),20); %linewidth
valdom{6} = logspace(log10(1),log10(60),20); %stimRadius
valdom{7} = [0 128 255];

state.valId = [1 1 1 1 12 9 2];  %Current index for each value domain
state.symId = 1;  %Current symbol index
%%%%%%%%%%%%%%%
%%%%%%%%%%%%%%%

%initialize the texture
for i = 1:length(valdom)
    symbol = symbList{i};
    val = valdom{i}(state.valId(i));
    updatePstate(symbol,num2str(val));
end



makeAngleTexture

symbol = symbList{state.symId};
val = valdom{state.symId}(state.valId(state.symId));
newtext = [symbol ' ' num2str(val)];


Screen(screenPTR, 'FillRect', valdom{7}(state.valId(7)))

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
       
        if strcmp(symbol,'background')
            if val==255
                updatePstate('redgain',num2str(0));
                updatePstate('bluegain',num2str(0));
                updatePstate('greengain',num2str(0));
            else
                updatePstate('redgain',num2str(1));
                updatePstate('bluegain',num2str(1));
                updatePstate('greengain',num2str(1));
            end
            Screen(screenPTR, 'FillRect', val)
        end
        
        
        updatePstate(symbol,num2str(val));
        
        if ~strcmp(symbol,'radius') 
            makeAngleTexture
        end
        
        
        
        newtext = [symbol ' ' num2str(val)];
        
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
        
        if strcmp(symbol,'background')
            if val==255
                updatePstate('redgain',num2str(0));
                updatePstate('bluegain',num2str(0));
                updatePstate('greengain',num2str(0));
            else
                updatePstate('redgain',num2str(1));
                updatePstate('bluegain',num2str(1));
                updatePstate('greengain',num2str(1));
            end
            Screen(screenPTR, 'FillRect', val)
        end
        
        updatePstate(symbol,num2str(val));
        
        if ~strcmp(symbol,'radius') 
            makeAngleTexture
        end
        
        
        
        newtext = [symbol ' ' num2str(val)];
        
        %Screen(screenPTR,'DrawText',newtext,40,30,255);
        %Screen('Flip', screenPTR);
    end
    
    
   
    stimSizecm=2*valdom{6}(state.valId(6))*2*pi/360*Mstate.screenDist;
    stimSize=round(stimSizecm*pixpercmX);
    
    xran = [mx-floor(stimSize/2)+1  mx+ceil(stimSize/2)];
    yran = [my-floor(stimSize/2)+1  my+ceil(stimSize/2)];
    
    %need to make sure not to leave the window
    if xran(1)<0
        xran=[0 stimSize];
    end
    if xran(2)>screenRes.width
        xran=[screenRes.width-stimSize screenRes.width];
    end
    if yran(1)<0
        yran=[0 stimSize];
    end
    if yran(2)>screenRes.height
        yran=[screenRes.height-stimSize screenRes.height];
    end
    
    
    StimLoc = [xran(1) yran(1) xran(2) yran(2)]';
    
    
    
   
    Screen('CopyWindow',screenPTROff,screenPTR,[],StimLoc);
    
    Screen(screenPTR,'DrawText',newtext,40,30,255-255*floor(valdom{7}(state.valId(7))/255));
    xypos = ['x ' num2str(mx) '; y ' num2str(my)];
    Screen(screenPTR,'DrawText',xypos,40,55,255-255*floor(valdom{7}(state.valId(7))/255));
    Screen('Flip', screenPTR);
    
    bLast = b;
    
    keyIsDown = KbCheck(-1);
    
end



%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
Screen(screenPTR, 'FillRect', Pstruct.background)
Screen(screenPTR, 'Flip');

Screen('Close')  %Get rid of all textures/offscreen windows

