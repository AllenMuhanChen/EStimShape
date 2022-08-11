function getResp_real(gaInfo,conn)
    getPaths;
    folderName = [gaInfo.currentExptPrefix '_r-' num2str(gaInfo.gaRun)];
    fullFolderPath = [folderName '_g-' num2str(gaInfo.genNum)];
    
    unitStat = 1; %#ok<NASGU>
    disp('Fetching stimulus and task order');
    [stimOrder,blankStimIdx,taskIds] = getStimOrder(gaInfo,conn);
    disp('Fetching data per task');
    [acqData,parsedData] = getAcqData(taskIds,conn); %#ok<ASGLU>
    disp('Parsing data into spike times per stimulus');
    [respStruct,taskStruct,resp,blankResp] = parseAcqData(parsedData,stimOrder,blankStimIdx,gaInfo.stimAndTrial.nStimPerTrial); %#ok<ASGLU>
    
    save([respPath '/' fullFolderPath '/acqData.mat'],'acqData','parsedData','taskStruct','stimOrder','taskIds','respStruct','blankStimIdx');
    save([respPath '/' fullFolderPath '/resp.mat'],'resp','blankResp','unitStat');
    
    save([secondaryPath '/resp/' fullFolderPath '/acqData.mat'],'acqData','parsedData','taskStruct','stimOrder','taskIds','respStruct','blankStimIdx');
    save([secondaryPath '/resp/' fullFolderPath '/resp.mat'],'resp','blankResp','unitStat');
end

function [stimOrder,blankStimIdx,taskIds] = getStimOrder(gaInfo,conn)
    setdbprefs('DataReturnFormat','numeric')
    firstTrialId = fetch(conn,['SELECT firstTrial FROM DescriptiveInfo WHERE gaRun = ' num2str(gaInfo.gaRun) ' AND genNum = ' num2str(gaInfo.genNum)]); 
    lastTrialId = fetch(conn,['SELECT lastTrial FROM DescriptiveInfo WHERE gaRun = ' num2str(gaInfo.gaRun) ' AND genNum = ' num2str(gaInfo.genNum)]); 
    setdbprefs('DataReturnFormat','cellarray')
    allStimSpec = fetch(conn,['SELECT id,extractvalue(spec, ''/StimSpec/object'') as ''ob'' '...
        'FROM stimspec WHERE id >= ' num2str(firstTrialId{1,1}) ' AND id <= ' num2str(lastTrialId{1,1})]);
    allStimSpec = table2cell(allStimSpec);
    nStimPerTrial = gaInfo.stimAndTrial.nStimPerTrial;
    nTrial = size(allStimSpec,1);
    trialOrder = cell(nTrial,nStimPerTrial);
    for ii=1:nTrial
        if nStimPerTrial == 4
            trialOrder(ii,:) = textscan(allStimSpec{ii,2}, '%s%s%s%s', 'delimiter', ' ');
        elseif nStimPerTrial == 2
            trialOrder(ii,:) = textscan(allStimSpec{ii,2}, '%s%s', 'delimiter', ' ');
        elseif nStimPerTrial == 3
            trialOrder(ii,:) = textscan(allStimSpec{ii,2}, '%s%s%s', 'delimiter', ' ');
        end
    end
    
    setdbprefs('DataReturnFormat','numeric')
    rungen = ['r-' num2str(gaInfo.gaRun) '_g-' num2str(gaInfo.genNum)];
    allStimObjIds = fetch(conn,['SELECT id FROM stimobjdata WHERE descId LIKE ''%' rungen '%''']);
    allStimObjIds = table2array(allStimObjIds);
    blankObjIds = fetch(conn,['SELECT id FROM stimobjdata WHERE descId LIKE ''%' rungen '%'' AND descId LIKE ''%_s-BLANK%''']);
    blankObjIds = table2array(blankObjIds);
    blankStimIdx = find(allStimObjIds == blankObjIds);
    
    nStim = length(allStimObjIds);
    nRep = gaInfo.stimAndTrial.nReps;
    
    stimOrder = nan(nStim,nRep,2);
    stimCounted = zeros(nStim,1);
    
    for ii=1:nTrial
        for jj=1:nStimPerTrial
            if isempty(trialOrder{ii,jj})
                continue;
            end
            stimIdx = find(allStimObjIds == str2double(trialOrder{ii,jj}));
            stimCounted(stimIdx) = stimCounted(stimIdx) + 1;
            stimOrder(stimIdx,stimCounted(stimIdx),:) = [ii jj];
        end
    end
    
    taskIds = cell2mat(allStimSpec(:,1));
end

function [acqData,parsedData] = getAcqData(taskIds,conn)
    nTask = length(taskIds);
    acqData = cell(nTask,1);
    parsedData = struct([]);
    for t=1:nTask
        setdbprefs('DataReturnFormat','numeric')
        tstamp = fetch(conn,['SELECT tstamp FROM taskdone WHERE task_id = ' num2str(taskIds(t)) ' AND part_done = 0']);
        while isempty(tstamp)
            disp(['Waiting for task ' num2str(t) '; id: ' num2str(taskIds(t))])
            pause(10);
            tstamp = fetch(conn,['SELECT tstamp FROM taskdone WHERE task_id = ' num2str(taskIds(t)) ' AND part_done = 0']);
        end
        fprintf('.')
        
        tstamp = table2array(tstamp);
        acqsess = fetch(conn,['SELECT * FROM acqsession WHERE start_time < ' num2str(tstamp) ' AND stop_time > ' num2str(tstamp)]);
        
        warning('off','all');
        % setdbprefs('FetchInBatches','no');
        setdbprefs('DataReturnFormat','cellarray')
        acqData{t} = getAcqDataForSess(acqsess,conn);
        entrySizeInBytes = 2 + 4 + 8;
        warning('on','all');

        nEntries = size(acqData{t},1) / entrySizeInBytes;
        data = zeros(nEntries, 3);

        row = 1;
        for n = 1:entrySizeInBytes:size(acqData{t},1)
            data(row, 1)  = typecast(acqData{t} (n:n+1), 'int16');
            data(row, 2)  = typecast(acqData{t} (n+2:n+5), 'int32');
            data(row, 3)  = typecast(acqData{t} (n+6:n+13), 'double');

            row = row + 1;
        end
        
        parsedData(t).marker1 = data(data(:,1) == 1 & data(:,3) > 0,2);
        parsedData(t).marker2 = data(data(:,1) == 2 & data(:,3) > 0,2);
        parsedData(t).spike = data(data(:,1) == 0 & data(:,3) > 0,2);
        
        % cla;
        % stem(parsedData(t).marker1,ones(length(parsedData(t).marker1),1),'r'); hold on;
        % stem(parsedData(t).marker2,ones(length(parsedData(t).marker2),1),'g')
        % scatter(parsedData(t).spike,2*ones(length(parsedData(t).spike),1),'b')
        
    end
    fprintf('\n');
end

function [respStruct,taskStruct,resp,blankResp] = parseAcqData(parsedData,stimOrder,blankStimIdx,nStimPerTask)
    nTask = length(parsedData);
    nStim = size(stimOrder,1);
    nRep = size(stimOrder,2);
    
    samplingRate = 25000;
    pre = 100/1000;
    post = 100/1000;
    
    taskStruct = struct([]);
    % respStruct = struct([]);
    
    resp = nan(nStim,1,nRep);
    blankResp = nan(1,1,nRep);
    
    for t=1:nTask
        
        % cla;
        % stem(parsedData(t).marker1,ones(length(parsedData(t).marker1),1),'r'); hold on;
        % stem(parsedData(t).marker2,ones(length(parsedData(t).marker2),1),'g')
        % scatter(parsedData(t).spike,2*ones(length(parsedData(t).spike),1),'b')
        
        
        [~,stimMarker] = max([parsedData(t).marker1;parsedData(t).marker2]);
        stimMarker = 1 + (stimMarker > length(parsedData(t).marker1));
        
        stimMarkerTstamps = eval(['parsedData(t).marker' num2str(stimMarker)]);
        % stem(stimMarkerTstamps,ones(length(stimMarkerTstamps),1),'r'); hold on;
        
        falling = find(diff(stimMarkerTstamps) > 2000);
        rising = falling + 1;
        
        if length(falling) > nStimPerTask
            falling = stimMarkerTstamps(falling(2:end));
            rising = stimMarkerTstamps(rising(1:end-1));
        end
        
        if length(rising) ~= nStimPerTask && t ~= nTask
            disp(['Something went wrong. More/less stimuli detected in task ' num2str(t) ' than expected.']);
        end
        
        % scatter(rising,0.5*ones(1,length(rising)),'b')
        % scatter(falling,0.5*ones(1,length(rising)),'g')
        for s=1:length(rising)
            preSpikes = (parsedData(t).spike(parsedData(t).spike > (rising(s) - (samplingRate*pre)) & parsedData(t).spike < rising(s)) - rising(s)) / samplingRate;
            spikes = (parsedData(t).spike(parsedData(t).spike > rising(s) & parsedData(t).spike < falling(s)) - rising(s)) / samplingRate;
            postSpikes = (parsedData(t).spike(parsedData(t).spike > falling(s) & parsedData(t).spike <  falling(s) + (samplingRate*post)) - rising(s)) / samplingRate;
            
            stimOnTime = (falling(s) - rising(s))/samplingRate;
            
            rate = length(spikes)/stimOnTime;
            
            taskStruct(t,s).preSpikes = preSpikes;
            taskStruct(t,s).spikes = spikes;
            taskStruct(t,s).postSpikes = postSpikes;
            taskStruct(t,s).stimOnTime = stimOnTime;
            taskStruct(t,s).rate = rate;
        end
    end
    
    for s=1:nStim
        for r=1:nRep
            taskNum = stimOrder(s,r,1);
            stimNum = stimOrder(s,r,2);
            
            resp(s,1,r) = taskStruct(taskNum,stimNum).rate;
            respStruct(s,r) = taskStruct(taskNum,stimNum); %#ok<AGROW>
        end
    end
    
    blankResp(1,1,:) = resp(blankStimIdx,:,:);
    resp(blankStimIdx,:,:) = [];
end

function acqData = getAcqDataForSess(acqsess,conn)
    acqsess = table2array(acqsess);
    a = fetch(conn,['SELECT data FROM acqdata WHERE tstamp > ' num2str(acqsess(1)) ' AND tstamp < ' num2str(acqsess(2))]);
    a = table2cell(a);
    if length(a) > 1
        acqData = cell2mat(a);
    else
        acqData = a{1,1};
    end
end