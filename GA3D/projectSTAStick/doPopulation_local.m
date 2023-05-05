clc; close all; clear;
loadedFile = load('data/ids.mat');
population = loadedFile.population;

%%
if exist('data/corrScores_dcn.mat','file')
    % ii is 0-indexed so that it is compatible with the cluster
    cellsToDo = 177; % [45,188,257,271,274,276];
    nJobs = length(cellsToDo);
    % corrScores = struct('s',0,'r',0,'t',0,'surf',0,'comb',0);
    % p = struct('s',0,'r',0,'t',0,'surf',0,'comb',0);
    for jobId=0:nJobs-1
        cellId = find([population.runNum] == cellsToDo(jobId+1));
        try
            temp1 = doSingleCell(cellId-1);
        catch
            temp1 = [];
        end
        if ~isempty(temp1)
            corrScores(jobId+1) = temp1;
        end
    end

    % save('data/corrScores_dcn.mat','corrScores')
else
    % load('data/corrScores_dcn.mat','corrScores')
end
%%
% doPopulation_corrScores
% doPopulation_corrScores_dcn