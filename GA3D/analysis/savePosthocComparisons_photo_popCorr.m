clc; close all; clear
if ~exist('plots/population/photo_pop.mat','file')
    lineCols = load('plots/population/ids.mat');
    population = lineCols.population;

    score_shape = [];
    score_cond = [];
    score_shuff = [];
    score_svd = [];
    % score_corr = struct([]);
    count = 1;
    for cc=1:length(population)
        if sum(population(cc).postHocIds == 6) > 0
            filePrefix = [num2str(population(cc).prefix) '_r-' num2str(population(cc).runNum)];
            disp([num2str(cc) ': ' filePrefix]);
            [shapeScore,condScore,shuffScore,svd_score,cellResp,sizePos_resp,shuffleResp,corrScore] = ...
                doSingleCell(num2str(population(cc).prefix),population(cc).runNum,population(cc).nGen,population(cc).nPostHoc,population(cc).postHocIds,40,population(cc).monkeyId); % allDCNCells(cc).bestCellResp);
            score_shape = [score_shape;shapeScore];
            score_cond = [score_cond;condScore];
            score_shuff = [score_shuff;shuffScore];
            score_svd = [score_svd;svd_score];
            score_corr(count) = corrScore;
            
            population(cc).resp = cellResp;
            population(cc).shuffleResp = shuffleResp;
            population(cc).sizePos_resp = sizePos_resp;
            cell(count) = population(cc);
            
            count = count + 1;
        end
    end

    save('plots/population/photo_pop.mat','score_shape','score_cond','score_shuff','score_svd','score_corr','cell');
else
    load('plots/population/photo_pop.mat','score_shape','score_cond','score_shuff','score_svd','score_corr','cell');
end

p = arrayfun(@(ii) signrank(score_corr(ii).shuf,score_corr(ii).sc),1:25);

%%
clf;
% subplot(121);
% set(gcf,'color','w','pos',[226,187,782,447]);
% histogram([score_corr.sc],linspace(-1,1,11),'LineWidth',2,'EdgeColor','none','FaceAlpha',0.8,'FaceColor','k'); hold on;
% histogram([score_corr.sc_chr],linspace(-1,1,11),'LineWidth',2,'EdgeColor','none','FaceAlpha',0.7,'FaceColor',[0.2 1 0.6]);
% histogram([score_corr.sc_gls],linspace(-1,1,11),'LineWidth',2,'EdgeColor','none','FaceAlpha',0.7,'FaceColor',[1 0.2 0.6]);
% fixPlot(gca,[-1.1 1.1],[0 8],'corr ga vs mean across photos','cell count',-1:0.5:1,0:2:8,'photo posthoc',{'all','chrome','glass'})
% grid on;
% 
% subplot(122);
sig = sum(([[score_corr.sc_chr_p]' [score_corr.sc_gls_p]'] < 0.05),2)==2;
a = [score_corr.sc_chr];
b = [score_corr.sc_gls];
plot(a,b,'.','markersize',20,'color',[0.7 0.7 0.7]); hold on;
plot(a(sig),b(sig),'k.','markersize',20); hold on;
fixPlot(gca,[-1 1],[-1 1],{'corr ga vs mean across'; 'reflective (chrome)'},{'corr ga vs mean across'; 'refractive (glass)'},-1:0.5:1,-1:0.5:1,'photo posthoc')
grid on;
% screen2png('plots/population/photo_gaVsMeanPhoto.png')

    


function [shapeScore,condScore,shuffScore,svd_score,resp,sizePos_resp,shuffleResp,corrScore] = ...
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

    [shapeScore,condScore,shuffScore,svd_score,resp,shuffleResp] = getPostHocResp(sData,linResp);
    [sizePos_resp,resp,shuffleResp] = getCorrectGAResp(sizePos_sData,sData,resp,shuffleResp);
    
    corrScore.sc = corr(mean(resp,2),sizePos_resp');
    [corrScore.sc_chr,corrScore.sc_chr_p] = corr(mean(resp(:,1:size(resp,2)/2),2),sizePos_resp');
    length(mean(resp(:,1:size(resp,2)/2),2))
    [corrScore.sc_gls,corrScore.sc_gls_p] = corr(mean(resp(:,(1+size(resp,2)/2) : end),2),sizePos_resp');
    corrScore.shuf = cellfun(@(x) corr(mean(x,2),sizePos_resp'),shuffleResp);
    corrScore.lm = fitlm(mean(resp,2),sizePos_resp);
    corrScore.rs = corrScore.lm.Rsquared.Ordinary;
    corrScore.constM = corrScore.lm.anova{1,5};
end

function [shapeScore,condScore,shuffScore,svd_score,resp,shResp] = getPostHocResp(sData,linResp)
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
    shuffleResp = reshape(resp(randperm(numel(resp))),size(resp));
    
    for ii=1:10
        aresp = mean(resp,2);
        temp = aresp(randperm(length(aresp)));
        % temp = mean(reshape(resp(randperm(numel(resp))),size(resp)),2);
        shResp{ii} = reshape(temp,[max(condGroup) max(parents)])';
    end
    resp = mean(resp,2);

    [~,t] = anovan(resp,{parents,condGroup},'display','off');
    shapeScore = t{2,6};
    condScore = t{3,6};
    
    % shuffleResp = resp(randperm(length(resp))); 
    [~,t] = anovan(mean(shuffleResp,2),{parents,condGroup},'display','off');
    shuffScore = t{2,6};
    
    resp = reshape(resp,[max(condGroup) max(parents)])';
    % imagesc(resp);
    [~,~,V] = svd(resp);
    v = diag(V);
    svd_score = v(1)^2/sum(v.^2);       
end

function [sizePos_resp,resp,shuffleResp] = getCorrectGAResp(sizePos_sData,sData,resp,shuffleResp)
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
    shuffleResp = cellfun(@(x) x/scaling,shuffleResp,'UniformOutput',false);
end

