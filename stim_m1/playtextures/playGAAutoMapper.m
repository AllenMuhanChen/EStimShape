function playGAAutoMapper
    global screenPTR screenNum Mstate daq screenPTROff2
    background = 0;
    
    Pstruct = getParamStruct;

    screenRes = Screen('Resolution',screenNum);
    pixpermmX = screenRes.width/(Mstate.screenXcm*10);
    pixpermmY = screenRes.height/(Mstate.screenYcm*10);
    
    nPos = 5; % nPos x nPos grid between -20deg to 20deg
    % if randPos is 1, nPos is ignored.
    nReps = 10;
    randShape = 1; % randomize position between -20deg and 20deg
    [stimX,stimY,stimN,stimS] = makeGAAutoMapper(nPos,nReps,randShape,round(pixpermmX),round(pixpermmX),Mstate.screenDist);

    nTrial = length(stimX);

    % blank screen
    Screen(screenPTR, 'FillRect', background);
    Screen('Flip', screenPTR);

    keyIsDown = 0;
    keyCode = 1;
    
    trialOff = 252;
    trialOn = 253;
    juice = 255;

    inferredTrialOnStatus = 0; % 0 = off; 1 = on
    inferredTrialCompleteStatus = 0; % 0 = break/fail; 1 = complete
    trialCount = 1;

    trialStatusChan = 1;

    dataCurrentStatus = [252 254];
    dataStatusChanged = 0;
    
    fixWidth = round(pixpermmX*2);
    fixHeight = round(pixpermmY*2);
    fixPos = [0 0];

    fixLoc = [screenRes.width-fixWidth/2 (screenRes.height-fixHeight)/2 ...
                (screenRes.width+fixWidth)/2 (screenRes.height+fixHeight)/2 ];
    fixPiece = [(screenRes.width-fixWidth)/2 (screenRes.height-fixHeight)/2 ...
                (screenRes.width+fixWidth)/2 (screenRes.height+fixHeight)/2 ];
    fixColor = zeros(fixHeight,fixWidth,3);
    fixColor(:,:,1:2) = 255;
    
    updatePstate('ori','0');
    updatePstate('fore_r','255');
    updatePstate('fore_g','255');
    updatePstate('fore_b','0');
    updatePstate('background',num2str(background));

    while trialCount <= nTrial % ~keyIsDown || ~strcmp(KbName(keyCode),'q') || 
        data = DaqDIn(daq, 2, 2);
        
        if ~isequal(data,dataCurrentStatus)
            dataStatusChanged = 1;
        else
            dataStatusChanged = 0;
        end
        dataCurrentStatus = data;
        
        if data(trialStatusChan) == trialOn
            if dataStatusChanged && ~inferredTrialOnStatus(trialCount) % if trial was previously off
                disp([num2str(trialCount) '/' num2str(nTrial) ': trial started']);
                inferredTrialOnStatus(trialCount) = 1;
            end

            updatePstate('stimnr',stimN(trialCount));
            updatePstate('xysize',stimS(trialCount));
            updatePstate('x_pos',stimX(trialCount));
            updatePstate('y_pos',stimY(trialCount));

            makeGAManualMapper;
            
            Screen('CopyWindow',screenPTROff2,screenPTR);
            
            texPointer = Screen(screenPTR, 'MakeTexture', fixColor);
            Screen('DrawTexture', screenPTR, texPointer,fixPiece,fixLoc);

            Screen('Flip', screenPTR);
        else
            if dataStatusChanged && data(trialStatusChan) == trialOff
                if inferredTrialCompleteStatus(trialCount)
                    disp([num2str(trialCount) '/' num2str(nTrial) ': trial ended - successful']);
                else
                    disp([num2str(trialCount) '/' num2str(nTrial) ': trial ended - break/fail']);
                end
                trialCount = trialCount + 1;
                disp(['Working at ' num2str(round(100*sum(inferredTrialCompleteStatus)/length(inferredTrialCompleteStatus))) '% correct']);
                
                inferredTrialOnStatus(trialCount) = 0;
                inferredTrialCompleteStatus(trialCount) = 0;
            elseif dataStatusChanged && data(trialStatusChan) == juice
                if inferredTrialCompleteStatus(trialCount)
                    disp([num2str(trialCount) '/' num2str(nTrial) ': bonus juice delivered']);
                else
                    inferredTrialCompleteStatus(trialCount) = 1;
                    disp([num2str(trialCount) '/' num2str(nTrial) ': juice delivered']);
                end
            end
                
            Screen(screenPTR, 'FillRect', background)
            Screen(screenPTR, 'Flip'); 
        end
        [keyIsDown,~, keyCode, ~] = KbCheck(-1);
    end

    taskDone = inferredTrialCompleteStatus(1:nTrial);
    cs = unique(stimS); ss = unique(stimN);
    perf = zeros(nC,nS);
    for c=1:nC
        indC = find(stimS == cs(c));
        for s=1:nS
            indS = find(stimN == ss(s));
            perf(c,s) = sum(taskDone(intersect(indC,indS)))/nReps;
        end
    end
    
    Screen(screenPTR, 'FillRect', background)
    Screen(screenPTR, 'Flip');

    Screen('Close')
    
    save(['/media/ConnorHome/Ramanujan/nutmegTrainingLog/' datestr(now,'yymmdd_hhMM') '.mat'],'perf','cs','ss');
end

function [fixX,fixY,fixS,fixC] = makeFixationContrastTest(nPos,nC,nS,nReps,randPos,pixpmmX,pixpmmY,screenDist)
    fixST1 = round(linspace(2,8,nS))';
    fixCT1 = 127 + round(linspace(-30,30,nC))';
    
    xlim = round(screenDist * 10 * tan(deg2rad(20))*pixpmmX);
    ylim = round(screenDist * 10 * tan(deg2rad(20))*pixpmmY);
    
    if randPos == 0 && nPos > 1
        fixXT1 = linspace(-xlim,xlim,nPos);
        fixYT1 = linspace(-ylim,ylim,nPos);
    else
        fixXT1 = 0; 
        fixYT1 = 0;
    end
    
    fixXT1 = fixXT1(:); fixYT1 = fixYT1(:);
    
    [fixXT2,fixYT2,fixST2,fixCT2] = ndgrid(fixXT1,fixYT1,fixST1,fixCT1);
    fixXT2 = fixXT2(:); fixYT2 = fixYT2(:); fixST2 = fixST2(:); fixCT2 = fixCT2(:);
    
    if randPos
        fixXT2 = datasample(linspace(-xlim,xlim,10),length(fixXT2))';
        fixYT2 = datasample(linspace(-ylim,ylim,10),length(fixYT2))';
    end
    
    fixX = [];
    fixY = [];
    fixS = [];
    fixC = [];
    
    nTrialsPerRep = length(fixXT2);
    
    for ii=1:nReps
        shuffleOrder = randperm(nTrialsPerRep);
        fixX = [fixX; fixXT2(shuffleOrder)];
        fixY = [fixY; fixYT2(shuffleOrder)];
        fixS = [fixS; fixST2(shuffleOrder)];
        fixC = [fixC; fixCT2(shuffleOrder)];
    end
end
