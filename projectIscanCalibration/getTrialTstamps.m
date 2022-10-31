function [tstamps,posB] = getTrialTstamps(conn,startTime)
    format long
    p.DataReturnFormat = 'cellarray';
    setdbprefs(p)

    
    tstamps = [];
    a = fetch(conn,['select * from BehMsg where tstamp > ' num2str(startTime)]);
    a = table2cell(a);
    trialCount = 0;
    pos = zeros(trialCount,2);
    for ii=1:length(a)
        if strcmp(a{ii,2},'CalibrationPointSetup')
           trialCount = trialCount + 1;
           pos(trialCount,1) = str2double(a{ii,3}(3+strfind(a{ii,3},'<x>'):strfind(a{ii,3},'</x>')-1));
           pos(trialCount,2) = str2double(a{ii,3}(3+strfind(a{ii,3},'<y>'):strfind(a{ii,3},'</y>')-1));
        elseif strcmp(a{ii,2},'FixationSucceed') && trialCount > 0
            tstamps(trialCount,1) = a{ii,1}; %#ok<*AGROW>
        elseif strcmp(a{ii,2},'TrialComplete') && trialCount > 0
            tstamps(trialCount,2) = a{ii,1};
        end
    end
    
    posB(:,1) = (sum(pos == repmat([0 0],size(pos,1),1),2) == 2);
    posB(:,2) = (sum(pos == repmat([5 0],size(pos,1),1),2) == 2);
    posB(:,3) = (sum(pos == repmat([-5 0],size(pos,1),1),2) == 2);
    posB(:,4) = (sum(pos == repmat([0 5],size(pos,1),1),2) == 2);
    posB(:,5) = (sum(pos == repmat([0 -5],size(pos,1),1),2) == 2);
end

