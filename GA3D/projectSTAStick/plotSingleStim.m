% prefix = 170624;
% runNum = 177;
% runId = [num2str(prefix) '_r-' num2str(runNum)];
% genNum = 2;
% linNum = 1;
% stimNum = 15;
function vert = plotSingleStim(h,runId,genNum,linNum,stimNum)
    cla(h); set(gcf,'Color','w','pos',[-1523,1,1145,1056])
    doPlot = true;

    imgpath = '/Users/ramanujan/Dropbox/Documents/Hopkins/NHP2PV4/projectXper/3dma/xper_sach7/xper-sach/images';
    stimpath = '/Users/ramanujan/Dropbox/Documents/Hopkins/NHP2PV4/projectMaskedGA3D/stim/dobby/';
%     resppath = '/Users/ramanujan/Dropbox/Documents/Hopkins/NHP2PV4/projectMaskedGA3D/resp/dobby/';
    jarpath = [pwd '/dep/fixShiftInDepth.jar'];
    datapath = [pwd '/data'];

    
    load([stimpath '/' runId '_g-' num2str(genNum) '/stimParams.mat']);
    stim = stimuli{linNum,stimNum};
    stimImgPath = [imgpath '/' runId '_g-' num2str(genNum) '/' num2str(stim.id.tstamp) '.png'];
    [num2str(genNum) num2str(linNum) num2str(stimNum) ' ' num2str(stim.id.tstamp)]
    
    fid = fopen([datapath '/' num2str(stim.id.tstamp) '_spec.xml'],'w+');
    fwrite(fid,stim.shape.mstickspec);
    fclose(fid);

    [~,shift] = system(['java -jar ' jarpath ' ' datapath ' ' num2str(stim.id.tstamp) ...
        ' ' num2str(stim.shape.x) ' ' num2str(stim.shape.y) ' ' num2str(stim.shape.s) ' true']);
    shift =  str2double(shift);

    vert = load(['data/' num2str(stim.id.tstamp) '_vert.txt']);
    face = load(['data/' num2str(stim.id.tstamp) '_face.txt']);
    x = stim.shape.x;
    y = stim.shape.y;
    z = -shift;
    s = stim.shape.s;

    vert = vert - repmat([x y z],size(vert,1),1);
    vert = vert / s;

    if doPlot
        hold(h,'on');
        % plot3(h,vert(:,1),vert(:,2),vert(:,3),'k.','MarkerSize',20);
        hp = patch('Faces',face,'Vertices',vert);
        hp.EdgeColor = 'none'; hp.FaceColor = [0.5 0.5 0.5];
        hp.FaceAlpha = 0.5;
        hp.FaceLighting = 'gouraud'; 
        hp.EdgeLighting = 'gouraud';
        hl = light;
        hl.Position = [0 5 5];
        axis(h,'equal'); view(h,0,90); axis(h,'off');
    end

    compPosTang = load(['data/' num2str(stim.id.tstamp) '_comp.txt']);

    specFileName = [datapath '/' num2str(stim.id.tstamp) '_spec.xml'];
    spec = xml2structedit(specFileName);
    mAxisInfo = spec.MStickSpec.mAxis;
    [brfields,~,nJunc,nEnd,~,~,~,~,~,~,mAxisRad,mAxisLen,tubeMidRad,...
        compPosTang] = parseStickSpec(mAxisInfo,compPosTang,doPlot,h);

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

    % data.genNum = genNum;
    % data.linNum = linNum;
    % data.stimNum = stimNum;
    % data.tstamp = stim.id.tstamp;
    % data.stim = stim;
    % data.texture = stim.shape.texture;
    % data.resp = resp;
    % data.x = x;
    % data.y = y;
    % data.z = z;
    % data.s = s;
    % data.vert = vert;
    % data.face = face;
    % data.comp = comp;
    % data.stimType = stimType;
    % data.fullComponents = compPosTang;
    % data.compLengths = mAxisLen;
    % data.compCurves = 1./mAxisRad;
    % data.shaftBis = shaftBis;
    % data.imgPath = stimImgPath;


    delete(['data/' num2str(stim.id.tstamp) '_vert.txt']);
    delete(['data/' num2str(stim.id.tstamp) '_face.txt']);
    delete(['data/' num2str(stim.id.tstamp) '_comp.txt']);
    delete(['data/' num2str(stim.id.tstamp) '_spec.xml']);

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
            % plot3([shaft.pos(1) tempPt(1)],[shaft.pos(2) tempPt(2)],[shaft.pos(3) tempPt(3)],'g-','linewidth',4);
        end
        
        comp(2*nComp+ii) = shaft;
    end
end
