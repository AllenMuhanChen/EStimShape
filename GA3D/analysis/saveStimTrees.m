function saveStimTrees()
    prefix = '170602';
    runNum = 133;
    nGen = 9;

    trees = buildStimTree(prefix,runNum,nGen);
    
    
end

function tree = buildStimTree(prefix,runNum,nGen)
    getPaths;
    folderName = [prefix '_r-' num2str(runNum)];

    parentIds = [];
    for genNum=1:nGen
        fullFolderName = [folderName '_g-' num2str(genNum)];

        rData(genNum) = load([respPath '/' fullFolderName '/resp.mat']); %#ok<AGROW>
        sData(genNum) = load([stimPath '/' fullFolderName '/stimParams.mat']); %#ok<AGROW>
        
        parentIds = [parentIds; getParentIds(sData(genNum))];
    end
    pids{1} = parentIds(:,1:2);
    pids{2} = parentIds(:,3:4);
    nStim = length(parentIds);
    nonControlIds = getNonControlIds(nGen);
    for l=1:2
        for ii=1:nStim
            id = pids{l}{ii,1};
            cids{ii,l} = find(ismember(pids{l}(:,2),id));
            cids{ii,l} = intersect(cids{ii,l},nonControlIds);
        end
    end
    
    count = 0;
    randIds = getRandIds(nGen);
    load(['trees/temp/stim/' num2str(prefix) '_r-' num2str(runNum) '_tempColFit.mat']);
    
    for linNum=1:2
        ids = [];    
        for ii=1:length(randIds) % length(cids) % 17:17
            id = randIds(ii);
            nodes = nan(length(cids),1);
            nodes(id) = 0;
            nodes = getNodes(id,cids(:,linNum),nodes);
    %         sons(id) = sum(~isnan(nodes));
            % treeplot(nodes);
            [fixedNodes,aliasNodes] = fixNodes(nodes);
            if length(unique(fixedNodes)) > 4
                ids = [ids;id];
                id
                figure;
                treeplot(fixedNodes','ko','k-'); hold on;
                [x,y] = treelayout(fixedNodes');
                for jj=1:length(x)
                    text(x(jj),y(jj),num2str(aliasNodes(jj)))
                end
                count = count + 1;
                tree(count).lin = linNum;
                tree(count).stim = id;
                tree(count).fNodes = fixedNodes;
                tree(count).aNodes = aliasNodes;
                
                if ~exist(['trees/temp/' num2str(id)],'dir'); mkdir(['trees/temp/' num2str(id)]); end
                
                eval(['resp = squeeze(mean(collatedRespLin' num2str(linNum) ',3));']);
                resp = resp(aliasNodes);
                cols = (resp - min(resp)) ./ (max(resp) - min(resp));
                colorLims = [min(resp) max(resp)];
                
                for jj=1:length(aliasNodes)
                    g = ceil(aliasNodes(jj)/40);
                    s = mod(aliasNodes(jj),40);
                    s(s==0) = 40;
                    
                    prg = [prefix '_r-' num2str(runNum) '_g-' num2str(g)];
                    load(['trees/temp/stim/' prg '/stimParams.mat']);
                    tstamp = stimuli{linNum,s}.id.tstamp;
                    
                    src = ['trees/temp/img/' prg '/' num2str(tstamp) '.png'];
                    dest = ['trees/temp/' num2str(id) '/' num2str(aliasNodes(jj)) '.png'];
                    copyfile(src,dest);
                    
                    im = imread(src);
                    im = imcrop(im,[150 150 300 300]);
                    im = addborderimage(im,30,255*[cols(jj) 0 0],'out');
                    image([x(jj)-0.05 x(jj)+0.05],[y(jj)+0.05 y(jj)-0.05],im);
                end
                axis square; axis off;
                % plot2svg(['trees/temp/' num2str(id) '/structure.svg']);
                saveas(gcf,['trees/temp/' num2str(id) '/' num2str(id) '_structure.svg']);
                saveas(gcf,['trees/temp/final/' num2str(id) '.svg']);
                close
            end
    %         treeplot(fixxedNodes');
        end
    end
%     
%     thumb = saveRasters(folderName, aliasNodes, 1);
%     
%     figure('pos',[816,765,246,246]);
%     for ii=1:length(aliasNodes)
%         clf
%         h = tight_subplot(1,1,0,0,0);
%         imshow(thumb(ii).im,'parent',h);
%         drawnow; screen2png(['withouttext/' num2str(thumb(ii).id) '.png']);
% %         text('units','pixels','position',[30 40],'fontsize',17,'string',[num2str(round(thumb(ii).resp,2)) '+-' num2str(round(thumb(ii).sem,2))],'color','c');
% %         drawnow; screen2png(['withtext/' num2str(thumb(ii).id) '.png']);
%     end
    
end

function parentIds = getParentIds(s)
    for ii=1:length(s.stimuli)
        parentIds{ii,1} = s.stimuli{1,ii}.id.descId;
        parentIds{ii,2} = s.stimuli{1,ii}.id.parentId;
        parentIds{ii,3} = s.stimuli{2,ii}.id.descId;
        parentIds{ii,4} = s.stimuli{2,ii}.id.parentId;
    end
end

function nodes = getNodes(id,cids,nodes)
    if ~isempty(cids{id})
        nodes(cids{id}) = id;
        for ii=1:length(cids{id})
            id2 = cids{id}(ii);
            nodes = getNodes(id2,cids,nodes);
        end
    end
end

function [fNodes,alias] = fixNodes(nodes)
    fNodes = nodes(~isnan(nodes));
    alias = find(~isnan(nodes));
    uniqueIds = unique(fNodes);
    for ii=2:length(uniqueIds)
        fNodes(fNodes==uniqueIds(ii)) = ii-1;
    end
    
end

function thumb = saveRasters(folderName, nodeIds, linNum)
    getPaths;
    load([stimPath '/' folderName '_tempColFit.mat'])
    eval(['r = mean(collatedRespLin' num2str(linNum) ',3);']);
    eval(['s = std(collatedRespLin' num2str(linNum) ',[],3)/sqrt(5);']);
    cols = (r - min(r)) / (max(r) - min(r));
    
    for ii=1:length(nodeIds)
        ss = nodeIds(ii);
        if mod(ss,40)
            genNum = floor(ss/40) + 1;
            stimNum = mod(ss,40);
        else
            genNum = floor(ss/40);
            stimNum = 40;
        end
        
        fullFolderName = [folderName '_g-' num2str(genNum)];
        load([stimPath '/' fullFolderName '/stimParams.mat']);
        tstamp = stimuli{linNum,stimNum}.id.tstamp;
        im = imread([thumbPath '/' fullFolderName '/' num2str(tstamp) '.png']);
        im = imcrop(im,[230 200 200 200]);
        im = addborderimage(im,30,255*[cols(ss) 0 0],'out');
        thumb(ii).id = ss;
        thumb(ii).gen = genNum;
        thumb(ii).stim = stimNum;
        thumb(ii).resp = r(ss);
        thumb(ii).sem = s(ss);
        thumb(ii).im = im;
    end
end

function nonControlIds = getNonControlIds(nGen)
    nonControlIds = 1:40;
    for ii=2:nGen
        nonControlIds = [nonControlIds (40*(ii-1) + 1):(40*ii - 20)];
    end
end

function randIds = getRandIds(nGen)
    randIds = 1:40;
    for ii=2:nGen
        randIds = [randIds (40*(ii-1) + 1):(40*(ii-1) + 4)];
    end
end