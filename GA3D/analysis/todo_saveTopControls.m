function todo_saveTopControls(folderName,sData,nGen,nLin,nStim,nControl)
    getPaths;
    allControlResp = nan(4,2*(nGen-1)*nControl/4,5);
    controlResp = nan(4,2*(nGen-1)*nControl/4);
    tstamp = nan(4,2*(nGen-1)*nControl/4);
    id = nan(4,2*(nGen-1)*nControl/4,3);
    
    firstControl = nStim-nControl+1;
    count = 1;
    for genNum=2:nGen
        for linNum=1:nLin
            for stimNum=firstControl:nStim
                [a,b] = ind2sub(size(controlResp),count);
                allControlResp(a,b,:) = sData(genNum).stimuli{linNum,stimNum}.id.respMatrix;
                controlResp(count) = mean(sData(genNum).stimuli{linNum,stimNum}.id.respMatrix);
                id(a,b,:) = [genNum linNum stimNum];
                tstamp(a,b) = sData(genNum).stimuli{linNum,stimNum}.id.tstamp;
                count = count + 1;
            end        
        end
    end
        save([plotPath '/' folderName '/' folderName '_allControls.mat'],'id','tstamp','allControlResp','controlResp');
    
    % cols = (controlResp - min(controlResp(:))) ./ (max(controlResp(:)) - min(controlResp));
    % nControlStim = size(controlResp,2);
    % hTopControls = figure('color','w','position',[680,628,1164,470]); 
    % ha = tight_subplot(2*(nGen-1),20,0.005,0.005,0.005);
    % for ii=1:nControlStim
    %     for jj=1:4
    %         h = ha(4*(ii-1)+jj);
    %         stimId = squeeze(id(jj,ii,:));
    %         im = imread([thumbPath '/' folderName '_g-' num2str(stimId(1)) '/' num2str(tstamp(jj,ii)) '.png']);
    %         im = imcrop(im,[150 150 300 300]);
    %         im = addborderimage(im,30,255*[cols(jj,ii) 0 0],'out');
    %         imshow(im,'parent',h);
    %     end
    % end
    % 
    % screen2png([plotPath '/' folderName '/' folderName '_topControls.png'],hTopControls);
    % close(hTopControls);
end