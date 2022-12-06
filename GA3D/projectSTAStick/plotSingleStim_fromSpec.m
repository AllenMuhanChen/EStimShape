% filePath = '/Users/ramanujan/Desktop/shadingImages/28';
function plotSingleStim_fromSpec(h,filePath)
    cla(h); set(gcf,'Color','w','pos',[-1523,1,1145,1056])
    doPlot = true;

    specFileName = [filePath '_spec.xml'];
    spec = xml2structedit(specFileName);
    mAxisInfo = spec.MStickSpec.mAxis;
    
    x = deg2rad(str2double(mAxisInfo.finalShiftInDepth.double{1}.Text));
    y = deg2rad(str2double(mAxisInfo.finalShiftInDepth.double{2}.Text));
    z = deg2rad(str2double(mAxisInfo.finalShiftInDepth.double{3}.Text));
    s = 15*3;
    
    vert = load([filePath '_vert.txt']);
    face = load([filePath '_face.txt']);

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

    compPosTang = load([filePath '_comp.txt']);

    [brfields,~,nJunc,nEnd,~,~,~,~,~,~,mAxisRad,mAxisLen,tubeMidRad,...
        compPosTang] = parseStickSpec(mAxisInfo,compPosTang,doPlot,h);

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
%             plot3([shaft.pos(1) tempPt(1)],[shaft.pos(2) tempPt(2)],[shaft.pos(3) tempPt(3)],'g-','linewidth',4);
        end
        
        comp(2*nComp+ii) = shaft;
    end
end
