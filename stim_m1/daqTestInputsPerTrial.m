function daqTestInputsPerTrial
    global daq
    % when using this test, change printLabels to 0, find the data values
    % at the various trial markers, and replace them. Then change
    % printLabels to 1 and check if the inferred trial status are correct.
    printLabels = 1;
    
    trialOff = 252;
    trialOn = 253;
    juice = 255;
    
    inferredTrialOnStatus = 0; % 0 = off; 1 = on
    inferredTrialCompleteStatus = 0; % 0 = break/fail; 1 = complete
    trialCount = 1;
    
    trialStatusChan = 1;
    
    currentDataStatus = [252 255];
    disp('Press q to exit test. Test starting...');
    keyIsDown = 0; keyCode = 1;
    while ~keyIsDown || ~strcmp(KbName(keyCode),'q')
        newData = DaqDIn(daq, 2, 2);
        if ~isequal(currentDataStatus,newData)
            if printLabels
                switch newData(trialStatusChan)
                    case trialOn
                        if ~inferredTrialOnStatus(trialCount) % if trial was previously off
                            disp([num2str(trialCount) ': trial started']);
                            inferredTrialOnStatus(trialCount) = 1;
                        end
                    case trialOff
                        if inferredTrialCompleteStatus(trialCount)
                            disp([num2str(trialCount) ': trial ended - successful']);
                        else
                            disp([num2str(trialCount) ': trial ended - break/fail']);
                        end
                        trialCount = trialCount + 1;
                        inferredTrialOnStatus(trialCount) = 0;
                        inferredTrialCompleteStatus(trialCount) = 0;
                    case juice
                        inferredTrialCompleteStatus(trialCount) = 1;
                        disp([num2str(trialCount) ': juice delivered']);
                end
            else
            	disp(newData);
            end
            currentDataStatus = newData;
        end
        [keyIsDown,~, keyCode, ~] = KbCheck(-1);
    end
end
