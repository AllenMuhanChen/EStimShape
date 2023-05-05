function sbxwswcb(src,callbackdata)

% scroll wheel callback

global bgimg data me va ku corrmap th_corr th_txt method mode_h


if(mode_h.Value==1) 
    th_corr = th_corr-callbackdata.VerticalScrollCount/50;
    th_corr = min(max(th_corr,0),1);
    %th_txt.String = sprintf('%1.2f',th_corr);
    
    p = gca;
    z = round(p.CurrentPoint);
    z = z(1,1:2);
    if(z(1)>0 && z(2)>0 && z(1)<796 && z(2)<512)
        cm = squeeze(sum(bsxfun(@times,data(z(2),z(1),:),data),3))/size(data,3);
        imgth = gather(cm>th_corr);
        bgimg.CData(:,:,2) = uint8(255*imgth);
        D = bwdistgeodesic(imgth,z(1,1),z(1,2));
        bw = imdilate(isfinite(D),strel('disk',1));
        bgimg.CData(:,:,3) = uint8(255*bw);
        drawnow;
    end
end
