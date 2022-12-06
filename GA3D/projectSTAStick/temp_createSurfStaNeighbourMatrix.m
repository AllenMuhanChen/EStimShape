function temp_createSurfStaNeighbourMatrix
    parfor jobId=1:1000
        createSurfStaNeighbourMatrix(jobId);
    end
end

function createSurfStaNeighbourMatrix(jobId)
    % each job does 3,840 entries
    % total 3,840,000 entries\
    % jobId 1: 1 - 1*3840
    % jobId 2: 1*3840+1 - 2*3840
    % jobId 3: 2*3840+1 - 3*3840
    % jobId n: 3840*(n-1) + 1 - 3840*n

    if ~exist(['dep/staNeigh/' num2str(jobId) '.mat'],'file')
        load('dep/neighbourCalc.mat');
        idsToDo = 3840*(jobId-1) + 1 : 3840*jobId;
        disp(['Job ' num2str(jobId) ' with ' num2str(length(idsToDo)) ' tasks.'])
        % % all these things are just loaded now. They can be generated from just binSpec
        % binCenters = binSpec.surf.binCenters;
        % [~,~,~,~,~,sphNeighbours] = getIcosphereDeets(1,0,0);
        % 
        % % all these shenanigans to get all the possible bin centers
        % % nothing to see here
        % str1 = '['; str2 = '('; str3 = '['; str4 = 'clearvars ';
        % binCount = 0;
        % for jj=1:length(binSpec.surf.nBin)
        %     if binSpec.surf.padding(jj) ~= 'i'
        %         binCount = binCount + 1;
        %         str1 = [str1 'b' num2str(binCount) ','];
        %         str2 = [str2 '1:length(binCenters{' num2str(jj) '}),'];
        %         str3 = [str3 'b' num2str(binCount) '(:),'];
        %         str4 = [str4 'b' num2str(binCount) ' '];
        %     end
        % end
        % str1 = [str1(1:end-1) ']'];
        % str2 = [str2(1:end-1) ');'];
        % str3 = [str3(1:end-1) '];'];
        % str4 = [str4(1:end-1) ';'];
        % 
        % eval([str1 ' = ndgrid' str2]);
        % eval(['allBins = ' str3]);
        % eval(str4);
        % % shenanigans over

        padding = binSpec.surf.padding;
        padding(padding == 'i') = '';
        staNeighMat = cell(1,length(idsToDo));
        for ii=1:length(idsToDo)
            binsToSmoothOver = zeros(size(allBins,1),1);
            for jj=1:length(padding)
                if padding(jj) == 's'
                    nei = find(sphNeighbours(allBins(idsToDo(ii),jj),:));
                    binsToSmoothOver = binsToSmoothOver + ismember(allBins(:,jj),nei);
                elseif padding(jj) ~= 'i'
                    binsToSmoothOver = binsToSmoothOver + (abs(allBins(:,jj) - allBins(idsToDo(ii),jj)) < 2);
                end
            end
            binsToSmoothOver = binsToSmoothOver == length(padding);
            binsToSmoothOver(idsToDo(ii)) = 0;
            staNeighMat{ii} = find(binsToSmoothOver);
        end
        save(['dep/staNeigh/' num2str(jobId) '.mat'],'staNeighMat');
    end
end