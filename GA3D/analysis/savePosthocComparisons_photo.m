function savePosthocComparisons_photo
    if ~exist('plots/population/photo_fstat.mat','file')
        
        lineCols = load('plots/population/ids.mat');
        population = lineCols.population;
        
        score_shape = [];
        score_cond = [];
        score_shuff = [];
        score_svd = [];
        count = 1;
        for cc=1:length(population)
            if sum(population(cc).postHocIds == 6) > 0
                filePrefix = [num2str(population(cc).prefix) '_r-' num2str(population(cc).runNum)];
                disp([num2str(cc) ': ' filePrefix]);
                [shapeScore,condScore,shuffScore,svd_score,cellResp,sizePos_resp] = doSingleCell(num2str(population(cc).prefix),population(cc).runNum,population(cc).nGen,population(cc).nPostHoc,population(cc).postHocIds,40,population(cc).monkeyId); % allDCNCells(cc).bestCellResp);
                score_shape = [score_shape;shapeScore];
                score_cond = [score_cond;condScore];
                score_shuff = [score_shuff;shuffScore];
                score_svd = [score_svd;svd_score];
                population(cc).resp = cellResp;
                population(cc).sizePos_resp = sizePos_resp;
                cell(count) = population(cc);
                count = count + 1;
            end
        end
        
        save('plots/population/photo_fstat.mat','score_shape','score_cond','score_shuff','score_svd','cell');
    else
        load('plots/population/photo_fstat.mat','score_shape','score_cond','score_shuff','score_svd','cell');
    end
    
    figure('color','w','pos',[1417,887,1117,440])
    
    subplot(121);
    h = cdfplot(score_shape); h.LineWidth = 2; hold on;
    h = cdfplot(score_shuff); h.LineWidth = 2; hold on;
    fixPlot(gca,'f-statistic for posthocs','probability',0:10:40,0:0.25:1,'f-statistic for photorealistic posthoc',{'real' 'shuffle'}); % {'Real cells' 'Best corresponding DCN cells'})    
    
    subplot(122);
    line([0 40],[0 40],'LineWidth',2,'color','k','linestyle',':'); hold on;
    plot(score_cond,score_shape,'.','MarkerSize',15)
    fixPlot(gca,'f-stat for condition','f-stat for 3D shape',0:10:40,0:10:40)
    axis equal; set(gca,'XLim',[0 40],'YLim',[0 40],'xtick',0:10:40,'ytick',0:10:40);
    
    screen2png('plots/population/photoF_cdf.png')
    close;
    
    figure('color','w','pos',[1417,887,1117,440])
    subplot(121);
    line([0 1],[0 1],'linewidth',2,'color','k','linestyle','--'); hold on
    lineCols = colormap('lines'); lineCols = lineCols(1:2,:);
    for cc=1:length(cell)
        [minResp,minId] = min(cell(cc).sizePos_resp);
        [maxResp,maxId] = max(cell(cc).sizePos_resp);
%         plot(minResp,maxResp,'b.','MarkerSize',20);
        maxResp = cell(cc).resp(maxId,:);
        minResp = cell(cc).resp(minId,:);
%         plot(minResp,maxResp,'y.','MarkerSize',5);
        
        mm_min = mean(minResp); ss_min = std(minResp)/sqrt(length(minResp));
        mm_max = mean(maxResp); ss_max = std(maxResp)/sqrt(length(maxResp));
        
        if mm_min > mm_max
            lineColor = lineCols(2,:);
        else
            lineColor = lineCols(1,:);
        end
        
        linWid = [mm_min - ss_min mm_min + ss_min];
        line([linWid(1) linWid(2)],[mm_max mm_max],'linewidth',2,'color',lineColor)
        linWid = [mm_max - ss_max mm_max + ss_max];
        line([mm_min mm_min],[linWid(1) linWid(2)],'linewidth',2,'color',lineColor)
        
        max_min(cc) = mm_max - mm_min;
        
        sig(cc) = ttest2(minResp,maxResp,'Tail','left','Alpha',0.05);
    end
    fixPlot(gca,'resp for min stim','resp for max stim',0:0.25:1,0:0.25:1)
    axis square
    
    subplot(122);
    h = histogram(max_min,10,'DisplayStyle','stairs','LineWidth',3);
    fixPlot(gca,'max - min resp','cell count',-1:0.5:1,0:5:10)
    
    screen2png('plots/population/photo_maxMin_clean.png')
    close
end

function [shapeScore,condScore,shuffScore,svd_score,resp,sizePos_resp] = ...
    doSingleCell(prefix,runNum,nGen,nPosthocs,postHocIds,nStim,monkeyId)
    
    getPaths;
    
    postHocGens = nGen-nPosthocs+1 : nGen;
    postHocGens = postHocGens(postHocIds == 6);
    
    folderName = [prefix '_r-' num2str(runNum)];

    sizePosGenNum = nGen - nPosthocs + 1;
    fullFolderName = [folderName '_g-' num2str(sizePosGenNum)];
    sizePos_sData = load([stimPath '/' fullFolderName '/stimParams.mat']);
    
    genResp = cell(1,length(postHocGens));
    for genNum=1:length(postHocGens)
        genId = postHocGens(genNum);
        fullFolderName = [folderName '_g-' num2str(genId)];

        rData = load([respPath '/' fullFolderName '/resp.mat']);
        sData = load([stimPath '/' fullFolderName '/stimParams.mat']);

        genResp{genNum} = squeeze(rData.resp);
    end
    genResp = cell2mat(genResp);
    linResp(:,:,1) = genResp(1:nStim,:);
    linResp(:,:,2) = genResp(nStim+1:2*nStim,:);

    [shapeScore,condScore,shuffScore,svd_score,resp] = getPostHocResp(sData,linResp);
    [sizePos_resp,resp] = getCorrectGAResp(sizePos_sData,sData,resp);
end

function [shapeScore,condScore,shuffScore,svd_score,resp] = getPostHocResp(sData,linResp)
    stim = [sData.stimuli{1,:}];
    ids = [stim.id];
    [~,~,parents] = unique({ids.parentId});

    % a saving bug has corrupted parent ids for second monkey. so just hardcode parents
    if max(parents) < 4
        parents = repmat(1:4,10,1); parents = parents(:);
    end
        
    parents = [parents; parents+max(parents)];
    condGroup = repmat(1:sum(parents==1),1,numel(parents)/sum(parents==1))';
    
    resp = squeeze(linResp(:,:,1));
    resp = [resp; squeeze(linResp(:,:,2))];
    resp = mean(resp,2);

    [~,t] = anovan(resp,{parents,condGroup},'display','off');
    shapeScore = t{2,6};
    condScore = t{3,6};
    
    shuffleResp = resp(randperm(length(resp))); 
    [~,t] = anovan(shuffleResp,{parents,condGroup},'display','off');
    shuffScore = t{2,6};
    
    resp = reshape(resp,[max(condGroup) max(parents)])';
    % imagesc(resp);
    [~,~,V] = svd(resp);
    v = diag(V);
    svd_score = v(1)^2/sum(v.^2);
end

function [sizePos_resp,resp] = getCorrectGAResp(sizePos_sData,sData,resp)
    xys = [sData.stimuli{1}.shape.x sData.stimuli{1}.shape.y sData.stimuli{1}.shape.s];
    
    stim_lin1 = [sData.stimuli{1,:}];
    ids = [stim_lin1.id];
    [~,~,parents] = unique({ids.parentId});
    
    % a saving bug has corrupted parent ids for second monkey. so just hardcode parents
    if max(parents) < 4
        parents = repmat(1:4,10,1); parents = parents(:);
    end
    
    nStim = sum(parents == 1);
    
    stim_lin1 = [sizePos_sData.stimuli{1,:}];
    stim_lin2 = [sizePos_sData.stimuli{2,:}];
    
    shapes = [stim_lin1.shape]; shapes = shapes(1:nStim);
    xys_all = [[shapes.x]' [shapes.y]' [shapes.s]'];
    
    [~,stimId] = ismember(xys,xys_all,'rows');
    
    ids = [stim_lin1.id]; ids = ids([0:nStim:39] + stimId);
    sizePos_resp = cellfun(@mean,{ids.respMatrix});
    
    ids = [stim_lin2.id]; ids = ids([0:nStim:39] + stimId);
    sizePos_resp = [sizePos_resp cellfun(@mean,{ids.respMatrix})];
    
    scaling = max([resp(:);sizePos_resp(:)]);
    sizePos_resp = sizePos_resp/scaling;
    resp = resp/scaling;
end

function fixPlot(h,xL,yL,xticks,yticks,titleStr,legendStr)
    h.LineWidth = 2; h.Color = 'w';
    h.XColor = 'k'; h.YColor = 'k';
    h.Box = 'off'; grid(h,'on');
    h.TickDir = 'out'; h.LineWidth = 2;
    
    h.FontSize = 10; h.FontName = 'Lato';
    
    h.XLabel.String = xL;
    h.XLabel.FontSize = 12; h.XLabel.FontName = 'Lato';
    h.YLabel.String = yL;
    h.YLabel.FontSize = 12; h.YLabel.FontName = 'Lato';
    
    if exist('xticks','var')
        h.XLim = [min(xticks) max(xticks)]; 
        h.XTick = xticks; 
    end
    
    if exist('yticks','var') && ~isempty(yticks)
        h.YLim = [min(yticks) max(yticks)];
        h.YTick = yticks; 
    end
    
    if exist('legendStr','var')
        hl = legend(h,legendStr);
        hl.FontSize = 13; hl.TextColor = 'k'; hl.Color = 'w'; hl.Box = 'off';
        hl.Location = 'SouthEast';
    end
    
    if exist('titleStr','var')
        ht = title(h,titleStr);
        ht.Interpreter = 'none';
        ht.Color = 'k'; ht.FontSize = 16; ht.FontName = 'Lato';
    end
end