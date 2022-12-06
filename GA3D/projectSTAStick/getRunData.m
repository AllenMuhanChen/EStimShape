% prefix = 170508;
% runNum = 45;
% nGen = 8;
function data = getRunData(prefix,runNum,nGen,monkeyId)
    nStim = 40;

    doPlot = false;

    imgpath = '/Users/ramanujan/Dropbox/Documents/Hopkins/NHP2PV4/projectXper/3dma/xper_sach7/xper-sach/images';
    if monkeyId == 1
        stimpath = '/Users/ramanujan/Dropbox/Documents/Hopkins/NHP2PV4/projectMaskedGA3D/stim/dobby/';
    elseif monkeyId == 2
        stimpath = '/Users/ramanujan/Dropbox/Documents/Hopkins/NHP2PV4/projectMaskedGA3D/stim/merri/';
    elseif monkeyId == 3
        stimpath = '/Users/ramanujan/Dropbox/Documents/Hopkins/NHP2PV4/projectMaskedGA3D/stim/gizmo/';
    end
%     resppath = '/Users/ramanujan/Dropbox/Documents/Hopkins/NHP2PV4/projectMaskedGA3D/resp/dobby/';
    jarpath = [pwd '/dep/fixShiftInDepth.jar'];
    datapath = [pwd '/data'];

    data = struct([]);
    disp(['Getting data for ' num2str(prefix) '_r-' num2str(runNum)]);
    
    stimCount = 1;
    for genNum=1:nGen
        load([stimpath '/' num2str(prefix) '_r-' num2str(runNum) '_g-' num2str(genNum) '/stimParams.mat']);
        disp(['... ' num2str(prefix) '_r-' num2str(runNum) '_g-' num2str(genNum)]);
        for linNum=1:2
            for stimNum=1:nStim
                stim = stimuli{linNum,stimNum};
                resp = stim.id.respMatrix;
                stimImgPath = [imgpath '/' num2str(prefix) '_r-' num2str(runNum) '_g-' num2str(genNum) '/' num2str(stim.id.tstamp) '.png'];

                fid = fopen([datapath '/' num2str(stim.id.tstamp) '_spec.xml'],'w+');
                fwrite(fid,stim.shape.mstickspec);
                fclose(fid);

                [~,shift] = system(['java -jar ' jarpath ' ' datapath ' ' num2str(stim.id.tstamp) ...
                    ' ' num2str(stim.shape.x) ' ' num2str(stim.shape.y) ' ' num2str(stim.shape.s) ' true']);
                shift =  str2double(shift);

                vert = load(['data/' num2str(stim.id.tstamp) '_vert.txt']);
                face = load(['data/' num2str(stim.id.tstamp) '_face.txt']);
                norm = load(['data/' num2str(stim.id.tstamp) '_norm.txt']);
                x = stim.shape.x;
                y = stim.shape.y;
                z = -shift;
                s = stim.shape.s;
                
                vert = vert - repmat([x y z],size(vert,1),1);
                vert = vert / s;

                if doPlot
                    clf; set(gcf,'color','k'); hold on;
                    scatter3(vert(:,1),vert(:,2),vert(:,3),'w.');
                    axis equal; view(0,90); axis off;
                end

                compPosTang = load(['data/' num2str(stim.id.tstamp) '_comp.txt']);

                specFileName = [datapath '/' num2str(stim.id.tstamp) '_spec.xml'];
                spec = xml2structedit(specFileName);
                mAxisInfo = spec.MStickSpec.mAxis;
                [brfields,~,nJunc,nEnd,~,~,~,~,~,~,mAxisRad,mAxisLen,tubeMidRad,...
                    compPosTang] = parseStickSpec(mAxisInfo,compPosTang,doPlot);

                stimType = getStimType(nEnd,nJunc);

                clearvars comp; comp = struct([]);
                for endNum=1:nEnd
                    comp(endNum).compNum = brfields.EnPts(endNum).comp;
                    comp(endNum).pos = brfields.EnPts(endNum).pos';
                    comp(endNum).tangent = brfields.EnPts(endNum).tangent';
                    comp(endNum).rad = brfields.EnPts(endNum).rad;
                    comp(endNum).end = brfields.EnPts(endNum).uNdx == 51;
                    comp(endNum).compPart = 'T';
                end
                tempCount = nEnd;
                for juncNum=1:nJunc
                    for ii=1:length(brfields.JPts(juncNum).comps)
                        tempCount = tempCount + 1;
                        comp(tempCount).compNum = brfields.JPts(juncNum).comps(ii);
                        comp(tempCount).pos = brfields.JPts(juncNum).pos';
                        comp(tempCount).tangent = brfields.JPts(juncNum).tang{ii}';
                        comp(tempCount).rad = brfields.JPts(juncNum).rad;
                        comp(tempCount).end = brfields.JPts(juncNum).uNdx(ii) == 51;
                        comp(tempCount).compPart = 'R';
                    end
                end
                [comp,shaftBis] = getShaftParams(comp,tubeMidRad,compPosTang,doPlot);

                data(stimCount).genNum = genNum;
                data(stimCount).linNum = linNum;
                data(stimCount).stimNum = stimNum;
                data(stimCount).tstamp = stim.id.tstamp;
                data(stimCount).stim = stim;
                data(stimCount).texture = stim.shape.texture;
                data(stimCount).resp = resp;
                data(stimCount).x = x;
                data(stimCount).y = y;
                data(stimCount).z = z;
                data(stimCount).s = s;
                data(stimCount).vert = vert;
                data(stimCount).face = face;
                data(stimCount).norm = norm;
                data(stimCount).comp = comp;
                data(stimCount).stimType = stimType;
                data(stimCount).fullComponents = compPosTang;
                data(stimCount).compLengths = mAxisLen;
                data(stimCount).compCurves = 1./mAxisRad;
                data(stimCount).shaftBis = shaftBis;
                data(stimCount).imgPath = stimImgPath;

                stimCount = stimCount + 1;
                
                delete(['data/' num2str(stim.id.tstamp) '_vert.txt']); 
                system(['rm -rf ~/.Trash/' num2str(stim.id.tstamp) '_vert.txt']);
                
                delete(['data/' num2str(stim.id.tstamp) '_norm.txt']);
                system(['rm -rf ~/.Trash/' num2str(stim.id.tstamp) '_norm.txt']);
                
                delete(['data/' num2str(stim.id.tstamp) '_face.txt']);
                system(['rm -rf ~/.Trash/' num2str(stim.id.tstamp) '_face.txt']);
                
                delete(['data/' num2str(stim.id.tstamp) '_comp.txt']);
                system(['rm -rf ~/.Trash/' num2str(stim.id.tstamp) '_comp.txt']);
                
                delete(['data/' num2str(stim.id.tstamp) '_spec.xml']);
                system(['rm -rf ~/.Trash/' num2str(stim.id.tstamp) '_spec.xml']);
            end
        end
    end
end

function stimType = getStimType(nEnd,nJunc)
    stimType = 0;
    
    if nEnd == 2
        switch(nJunc)
            case 1; stimType = 1;
            case 2; stimType = 2;
            case 3; stimType = 3;
        end
    elseif nEnd == 3
        switch(nJunc)
            case 1; stimType = 4;
            case 2; stimType = 5;
        end
    elseif nEnd == 4
        stimType = 6;
    end
end

function [comp,shaftBis] = getShaftParams(comp,tubeMidRad,compPosTang,doPlot)
    nComp = length(comp)/2;
    shaftBis = nan(nComp,3);
    
    for ii=1:nComp
        shaft.compNum = ii;
        shaft.pos = compPosTang(ii).pts(26,:);
        shaft.tangent = compPosTang(ii).tang(26,:);
        shaft.rad = tubeMidRad(ii);
        shaft.end = 0.5;
        shaft.compPart = 'S';
        
        ends = find([comp.compNum] == ii);
        vec = nan(length(ends),3);
        for cc=1:length(ends)
            if comp(ends(cc)).compPart == 'R'
                vec(cc,:) = -comp(ends(cc)).tangent;
            else
                vec(cc,:) = comp(ends(cc)).tangent;
            end
        end
        bis = round(sum(vec),5);
        bis = bis/norm(bis);
        shaftBis(ii,:) = bis;
        
        if doPlot
            tempPt = shaft.pos + bis.*0.5;
            plot3([shaft.pos(1) tempPt(1)],[shaft.pos(2) tempPt(2)],[shaft.pos(3) tempPt(3)],'g-','linewidth',4);
        end
        
        comp(2*nComp+ii) = shaft;
    end
end
