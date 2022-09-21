function playFixationContrastTest
    global screenPTR screenNum Mstate daq
    background = 127;

    screenRes = Screen('Resolution',screenNum);
    pixpermmX = screenRes.width/(Mstate.screenXcm*10);
    pixpermmY = screenRes.height/(Mstate.screenYcm*10);
    
    nPos = 1; % nPos x nPos grid between -20deg to 20deg
    % if randPos is 1, nPos is ignored.
    nC = 5; % number of contrasts (always odd number so that 127 is one of them)
    nS = 5; % number of sizes
    nReps = 10;
    randPos = 1; % randomize position between -20deg and 20deg
    [fixX,fixY,fixS,fixC] = makeFixationContrastTest(nPos,nC,nS,nReps,randPos,round(pixpermmX),round(pixpermmX),Mstate.screenDist);

    nTrial = length(fixX);

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


            fixWidth = round(pixpermmX*fixS(trialCount));
            fixHeight = round(pixpermmY*fixS(trialCount));

            fixLoc = [(screenRes.width+fixX(trialCount)-fixWidth)/2 (screenRes.height+fixY(trialCount)-fixHeight)/2 ...
                        (screenRes.width+fixX(trialCount)+fixWidth)/2 (screenRes.height+fixY(trialCount)+fixHeight)/2 ];
            fixPiece = [(screenRes.width+fixX(trialCount)-fixWidth)/2 (screenRes.height+fixY(trialCount)-fixHeight)/2 ...
                        (screenRes.width+fixX(trialCount)+fixWidth)/2 (screenRes.height+fixY(trialCount)+fixHeight)/2 ];
            fixColor = zeros(fixHeight,fixWidth,3);
            fixColor(:,:,:) = fixC(trialCount);

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
    cs = unique(fixC); ss = unique(fixS);
    perf = zeros(nC,nS);
    for c=1:nC
        indC = find(fixC == cs(c));
        for s=1:nS
            indS = find(fixS == ss(s));
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
