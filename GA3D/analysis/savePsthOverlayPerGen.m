function savePsthOverlayPerGen(nStim,linNum,aData,cols,folderName,fullFolderName)
    getPaths;
    hPsthOverlay = figure('color',[0.2 0.2 0.2],'position',[1372,55,530,420]);
    hPsth = gca; hold(hPsth,'on');
    psthFilePath = [plotPath '/' folderName '/' fullFolderName '/' fullFolderName '_l-' num2str(linNum) '_psthOverlay.png'];
    for stimNum=1:nStim
        stimNum2x = nStim*(linNum-1) + stimNum;
        acq = aData.respStruct(stimNum2x + 1,:);
        stimCol = cols(stimNum2x);
        
        getPsthPerStim(acq,stimCol,hPsth);
        
    end
    
    set(hPsth,'tickDir','out','color',[0.2 0.2 0.2],'xcolor','w','ycolor','w',...
        'box','off','fontname','lato','fontsize',16,'linewidth',3,...
        'ticklength',[0.02 0.02],'xlim',[-0.25 1],'ylim',[0 1],...
        'xtick',[0 0.75 1]);
    
    xlabel(hPsth,'Time (s)','fontname','lato','fontsize',16,'color','w'); 
    ylabel(hPsth,'Probability','fontname','lato','fontsize',16,'color','w'); 
    title(hPsth,'PSTH','fontname','lato','fontsize',20,'color','w','interpreter','none'); 
    
    screen2png(psthFilePath,hPsthOverlay);
    close(hPsthOverlay);
end

function getPsthPerStim(acq,normFactor,hPsth)
    spikes = cell(length(acq),1);
    for rep=1:length(acq)
        spikes{rep} = [acq(rep).preSpikes; acq(rep).spikes; acq(rep).postSpikes];
    end

    time = linspace(-0.25,1,1000);
    psth = zeros(1,1000);

    for rep=1:length(acq)
        psth = addSpikesToPsth(psth,time,spikes{rep});
    end
    psth = (psth - min(psth)) / (max(psth) - min(psth));
    psth = psth * normFactor;
    
    plot(hPsth,time,psth,'linewidth',1,'color',[normFactor 0 0]);
end

function psth = addSpikesToPsth(psth,time,spikes)
    for s=1:length(spikes)
        psth = psth + getGaussian([1,spikes(s),0.03],time);
    end
end
