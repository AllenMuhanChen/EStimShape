
function sbxwbmcb(src,callbackdata)

% during mouse movement

warning off;

global segmenttool_h roimask data nhood frames options th_corr bgimg mode_h zimg hline vline;

if(mode_h.Value == 1)
    p = gca;
    z = round(p.CurrentPoint);
    z = z(1,1:2);
    if(z(1)>0 && z(2)>0 && z(1)<796 && z(2)<512)
        try
        cm = squeeze(sum(bsxfun(@times,data(z(2),z(1),:),data),3))/size(data,3);
        imgth = gather(cm>th_corr);
        if(isempty(roimask))
            bgimg.CData(:,:,2) = uint8(255*imgth);
        else
            bgimg.CData(:,:,2) = uint8(255*imgth.*roimask);
        end
        D = bwdistgeodesic(imgth,z(1,1),z(1,2));
        bw = imdilate(isfinite(D),strel('disk',1));
        if(isempty(roimask))
            bgimg.CData(:,:,3) = uint8(255*bw);
        else
            bgimg.CData(:,:,3) = uint8(255*bw.*roimask);
        end
        % move axis...
        set(zimg.Parent,'xlim',[z(1)-32 z(1)+32],'ylim',[z(2)-32 z(2)+32]);        
        set(hline,'xdata',[z(1)-32 z(1)+32],'ydata', [z(2) z(2)]);
        set(vline,'ydata',[z(2)-32 z(2)+32],'xdata', [z(1) z(1)]);
        
        drawnow;
        catch
        end
        
    end
end