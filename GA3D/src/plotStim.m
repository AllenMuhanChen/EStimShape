function occluderPix = plotStim(hImage,hSchematic,stim)
    if ~isempty(hSchematic)
        hold(hSchematic,'on');
        
        % shape
        densePts = stim.shape.dPts;
        patch(densePts(:,1),densePts(:,2),stim.shape(1).color,'parent',hSchematic); alpha(0.5);
        axis(hSchematic,'image'); box(hSchematic,'on')
        
        % masks
        drawCircle(hSchematic,stim.mask(1).x,stim.mask(1).y,stim.mask(1).s,'c');
        drawCircle(hSchematic,stim.mask(2).x,stim.mask(2).y,stim.mask(2).s,'c');
        
        set(hSchematic,'color','k','xtick',[],'ytick',[]);
    end
    
    if ~isempty(hImage)
        hold(hImage,'on');
        set(hImage,'color',[0.8 0.8 0.8],'xtick',[],'ytick',[]);

        nStimPix = 100;
        occluderLims.x = [stim.occluder.leftBottom(1) stim.occluder.rightTop(1)];
        occluderLims.y = [stim.occluder.leftBottom(2) stim.occluder.rightTop(2)];
        
        [X,Y] = meshgrid(linspace(occluderLims.x(1),occluderLims.x(2),nStimPix),linspace(occluderLims.y(1),occluderLims.y(2),nStimPix));
        X = X(:); Y = Y(:);
        
        densePts = stim.shape.dPts;
        patch(densePts(:,1),densePts(:,2),stim.shape(1).color,'parent',hImage,'edgecolor','none');
        
        occluderPix = drawOccluder(stim.mask,nStimPix,X,Y);
        
        image('xdata',occluderLims.x,'ydata',fliplr(occluderLims.y),'cdata',zeros(nStimPix,nStimPix,3),'alphadata',flipud(occluderPix),'parent',hImage);
        axis(hImage,'image'); box(hImage,'on');

    end
end

function occluderPix = drawOccluder(masks,nStimPix,X,Y)
    occluderPix = ones(nStimPix);
    for s=1:length(masks)
        occluderPix((X - masks(s).x).^2 + (Y-masks(s).y).^2 < (0.9*masks(s).s)^2) = 0;
    end
    occluderPix = smoothOccluder(occluderPix,nStimPix/100);
end

function alphaOccluder = smoothOccluder(alphaOccluder,kernelWidth)
    kernel = ones(2*kernelWidth + 1)/(2*kernelWidth + 1);
    alphaOccluder = padarray(alphaOccluder,[kernelWidth kernelWidth],'replicate');
    alphaOccluder = convn(alphaOccluder,squeeze(kernel),'valid');
    alphaOccluder = alphaOccluder/(2*kernelWidth + 1);
end

