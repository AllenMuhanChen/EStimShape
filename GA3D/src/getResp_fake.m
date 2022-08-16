function [resp,blankResp,unitStat,times,blankTimes,respRange] = getResp_fake(s,n,t,nChunk,isTcAvailable)
    % blank repeats are 10 x stim repeats because blanks are run for each
    % chunk.
    unitStat = ones(1,n);

    if isTcAvailable
        times = zeros(1,1,1,41);
        times(1,1,1,:) = -1000:50:1000;
        times = repmat(times,[s,n,t]);

        blankTimes = zeros(1,1,1,41);
        blankTimes(1,1,1,:) = -1000:50:1000;
        blankTimes = repmat(blankTimes,[1,n,t]);

        resp = zeros(size(times));
        resp(times > 200 & times < 700) = 1;
        resp = resp .* repmat(rand(s,n),[1,1,t,41]) + 0.1*rand(s,n,t,41);

        blankResp = 0.1*rand(1,n,t,41);

        respRange = [200 700];
    else
        fracNoTrialsDone = 1/40; % fraction of stim that are not done
        fracSomeTrialsDone = 1/20; % fraction of stim that have some trials not done
        fracBlankNotDone = 1/20;
        
        resp = zeros(s,n);
        for ii=1:n
            resp(randperm(s,floor(s/10)),ii) = randi(10);
        end
%         imagesc(resp); colorbar
        resp = repmat(resp,1,1,t);
        resp = resp + resp.*rand(size(resp));
        resp = resp + rand(size(resp));

        sNotDone = sort(randperm(s,floor(s*fracNoTrialsDone)));
        resp(sNotDone,:,:) = nan;
        
        sPartDone = sort(randperm(s,floor(s*fracSomeTrialsDone)));
        for ii=1:length(sPartDone)
            trialIdxNotDone = randperm(t,randi(t-1));
            resp(ii,:,trialIdxNotDone) = nan;
        end
        
        resp = rand(s,n,t);
        nBlank = floor(t*(2*s/nChunk)); % 2*n / 100 is nChunk
        blankResp = 0.1*rand(1,n,nBlank); 
        blankIdxNotDone = randperm(nBlank,floor(nBlank*fracBlankNotDone));
        blankResp(1,:,blankIdxNotDone) = nan;
        
        
        times = [];
        blankTimes = [];
        respRange = [];
    end
end

