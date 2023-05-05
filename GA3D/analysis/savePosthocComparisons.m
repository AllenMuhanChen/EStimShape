function savePosthocComparisons(linNum,genNum,sData,thumb,posthocId,nPosthocStim,folderName,fullFolderName)
    getPaths;
    
    [conditions,name] = getConditionNames(posthocId);
    nStim = size(sData(genNum).stimuli,2);
    
    hPosthocComparisons = figure('color','w','pos',[1,301,1920,804],'name',[name ' posthoc']);
    figure(hPosthocComparisons); clf(hPosthocComparisons);
    ha = tight_subplot(nPosthocStim,nStim/nPosthocStim,0.005,[0.005 0.05],0.005);
    
    for stimNum=1:nStim
        m = mean(sData(genNum).stimuli{linNum,stimNum}.id.respMatrix);
        s = std(sData(genNum).stimuli{linNum,stimNum}.id.respMatrix)/sqrt(5);
        imshow(thumb{linNum,stimNum},'parent',ha(stimNum));
        text('units','pixels','position',[23 28],'fontsize',13,'string',num2str(stimNum),'color','c','parent',ha(stimNum));
        text('units','pixels','position',[23 153],'fontsize',13,'string',[num2str(round(m,2)) '+-' num2str(round(s,2))],'color','c','parent',ha(stimNum));
        if stimNum <= nStim/nPosthocStim
            title(ha(stimNum),conditions{stimNum},'fontsize',20,'fontname','lato');
        end
    end
    screen2png([plotPath '/' folderName '/' fullFolderName '/' fullFolderName '_l-' num2str(linNum) '_allStim.png'],hPosthocComparisons);
    close(hPosthocComparisons);
end

function [conditions,name] = getConditionNames(posthocId)
    switch(posthocId)
        case 1;  conditions = {'center 1x','right','left','top','bottom','center 2x','right','left','top','bottom'}; name = 'size position';
        case 2;  conditions = {'NE','N','NW','W','SW','S','SE','E'}; name = 'position grid';
        case 3;  conditions = {'center 1x','top lit','bottom lit','right lit','left lit','center 2x','center 3x','center 4x'}; name = 'size lighting';
        case 4;  conditions = {'3d deep','3d middle deep','3d middle front','3d front','3D RDK','2d deep','2d middle deep','2d middle front','2d front','2D RDK'}; name = 'RDS';
        case 6;  conditions = {'mirror closed','mirror grass','mirror soil','mirror','mirror corrugated','glass closed','glass grass','glass soil','glass','glass corrugated'}; name = 'photo';        
        case 8;  conditions = {'masked','masked','masked','masked','masked','masked','masked','masked'}; name = 'occlusion';
        case 9;  conditions = {'2','4','6','8','10','3d 2','3d 4','3d 6','3d 8','3d 10'}; name = 'contrast';
        case 10; conditions = {'zucker 2d','zucker 3d','orig light 2d','orig 3d','thin','thick','pointy','balloon-dog','dumb-bell','thick-end'}; name = 'zucker/radius';
    end
    
end

function [conditions,name] = getConditionNames_nVariant8(posthocId)
    switch(posthocId)
        case 1; conditions = {'center 1x','right','left','top','bottom','center 2x','center 3x','center 4x'}; name = 'size position';
        case 2; conditions = {'NE','N','NW','W','SW','S','SE','E'}; name = 'position grid';
        case 3; conditions = {'center 1x','top lit','bottom lit','right lit','left lit','center 2x','center 3x','center 4x'}; name = 'size lighting';
        case 4; conditions = {'3d behind','3d behind','3d middle','3d front','2d behind','2d behind','2d middle','2d front'}; name = 'RDS';
        case 6; conditions = {'2 walls + floor','2 walls + floor','2 walls + floor','open dense grass','open sparse grass','open','plain','corrugated'}; name = 'photo';        
        case 8; conditions = {'masked','masked','masked','masked','masked','masked','masked','masked'}; name = 'occlusion';
        case 9; conditions = {'0.1','0.2','0.4','0.5','0.6','0.7','0.8','0.9'}; name = 'contrast';
    end
    
end