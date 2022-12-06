function thumb = saveRastersPerGen(nStim,nLin,linNum,genNum,sData,rData,aData,postHocId,folderName,fullFolderName,cols,doSavePerStim)
    monkeyId = 3;
    getPaths;
    thumb = cell(nLin,nStim);
    hRaster = figure('color','k','position',[167,160,1435,420]);
    for stimNum=1:nStim
        stimNum2x = nStim*(linNum-1) + stimNum;
        stim = sData(genNum).stimuli{linNum,stimNum};
        resp = squeeze(rData(genNum).resp(stimNum2x,:,:));

        if postHocId == 6
            im = imread([stimPath '/' fullFolderName '/thumbnails/' fullFolderName '_photo/' fullFolderName '_l-' num2str(linNum) '_s-' num2str(stimNum) '.png']);
            im = imcrop(im,[790 240 500 500]);
        elseif postHocId == 10 && (mod(stimNum,10) == 1 || mod(stimNum,10) == 2)
            im = imread([stimPath '/' fullFolderName '/thumbnails/' fullFolderName '_drape/' fullFolderName '_l-' num2str(linNum) '_s-' num2str(stimNum) '.png']);
            im = imcrop(im,[790 240 500 500]);
        else
            im = imread([thumbPath '/' fullFolderName '/' num2str(stim.id.tstamp) '.png']);
            im = imcrop(im,[150 150 300 300]);
        end

        im = addborderimage(im,30,255*[cols(stimNum2x) 0 0],'out');
        thumb{linNum,stimNum} = im;
        stimCol = cols(stimNum2x);
        rasterFilePath = [plotPath '/' folderName '/' fullFolderName '/rasters/' fullFolderName '_l-' num2str(linNum) '_s-' num2str(stimNum) '.png'];
        if doSavePerStim
            acq = aData.respStruct(stimNum2x + 1,:);
            saveRastersPerStim(stim,resp,acq,thumb{linNum,stimNum},stimCol,rasterFilePath,hRaster);
        end
    end
    close(hRaster);
end

function saveRastersPerStim(stim,resp,acq,thumb,normFactor,filePath,hRaster)
    clf(hRaster);
    ha(1) = subplot(131);
    thumb = addborderimage(thumb,3,[255 255 255],'out');
    imshow(thumb,'parent',ha(1));
    m = mean(resp);
    s = std(resp)/sqrt(length(resp));
    text('units','pixels','position',[40 50],'fontsize',17,'string',num2str(stim.id.genNum),'color','c','parent',ha(1));
    text('units','pixels','position',[260 50],'fontsize',17,'string',num2str(stim.id.stimNum),'color','c','parent',ha(1));
    text('units','pixels','position',[40 260],'fontsize',17,'string',[num2str(round(m,2)) '+-' num2str(round(s,2))],'color','c','parent',ha(1));
    ha(2) = subplot(132);
    hold(ha(2),'on')

    spikes = cell(length(acq),1);
    for rep=1:length(acq)
        spikes{rep} = [acq(rep).preSpikes; acq(rep).spikes; acq(rep).postSpikes];
        for ii=1:length(spikes{rep})
            line([spikes{rep}(ii) spikes{rep}(ii)],[rep-0.5 rep+0.5],...
                'color','w','linewidth',2,'parent',ha(2));
        end
    end

    if stim.id.posthocId == 4 % || stim.id.posthocId == 6
        t = 2;
    else
        t = 1;
    end

    set(ha(2),'tickDir','out','color','k','xcolor','w','ycolor','w',...
        'box','off','fontname','lato','fontsize',16,'linewidth',3,...
        'ticklength',[0.02 0.02],'xlim',[-0.25 t],...
        'ylim',[0.5 length(acq)+0.5],'xtick',[0 0.75 1],'ytick',1:5);

    xlabel(ha(2),'Time (s)','fontname','lato','fontsize',16,'color','w');
    ylabel(ha(2),'Trials','fontname','lato','fontsize',16,'color','w');
    title(ha(2),stim.id.descId,'fontname','lato','fontsize',20,'color','w','interpreter','none');

    time = linspace(-0.25,t,t*1000);
    psth = zeros(1,t*1000);

    for rep=1:length(acq)
        psth = addSpikesToPsth(psth,time,spikes{rep});
    end
    psth = (psth - min(psth)) / (max(psth) - min(psth));
    psth = psth * normFactor;

    ha(3) = subplot(133);
    plot(ha(3),time,psth,'linewidth',3);

    set(ha(3),'tickDir','out','color','k','xcolor','w','ycolor','w',...
        'box','off','fontname','lato','fontsize',16,'linewidth',3,...
        'ticklength',[0.02 0.02],'xlim',[-0.25 t],'ylim',[0 1],...
        'xtick',[0 0.75 1]);

    xlabel(ha(3),'Time (s)','fontname','lato','fontsize',16,'color','w');
    ylabel(ha(3),'Probability','fontname','lato','fontsize',16,'color','w');
    title(ha(3),'PSTH','fontname','lato','fontsize',20,'color','w','interpreter','none');

    screen2png(filePath,hRaster);
end

function psth = addSpikesToPsth(psth,time,spikes)
    for s=1:length(spikes)
        psth = psth + getGaussian([1,spikes(s),0.03],time);
    end
end
