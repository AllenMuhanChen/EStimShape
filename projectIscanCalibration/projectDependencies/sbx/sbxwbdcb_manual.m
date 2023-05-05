function sbxwbdcb(src,callbackdata)

% button down

global bgimg mask oldcmap
global ncell cellpoly status segmenttool_h data mode_h

p = gca;
if(mode_h.Value ==1)
    z = round(p.CurrentPoint);
    z = z(1,1:2);
    m = findobj(segmenttool_h,'tag','method');
    if(z(1)>0 && z(2)>0 && z(1)<796 && z(2)<512)
        switch m.Value
            case 1  
                
            case 2
              
            case 3
                
                ncell = ncell+1;
                bw = bgimg.CData(:,:,3);
%                 B = bwboundaries(bw);
%                 xy = B{1};
                hp = imfreehand('Closed',true);
                xy = hp.getPosition;
                delete(hp);
                
                hold(bgimg.Parent,'on');
                h = patch(xy(:,2),xy(:,1),'white','facecolor',[1 .7 .7],'facealpha',0.7,'edgecolor',[1 1 1],'parent',bgimg.Parent,'FaceLighting','none','userdata',ncell,'tag','apatch');
                cellpoly{ncell} = h;
                [xx,yy] = meshgrid(1:size(mask,2),1:size(mask,1));
                bw=(inpolygon(xx,yy,xy(:,2),xy(:,1)));
                mask(bw) = ncell;
                hold(bgimg.Parent,'off');
                
                %do the same for zimg
                global zimg
                hold(zimg.Parent,'on');
                patch(xy(:,2),xy(:,1),'white','facecolor',[1 .7 .7],'facealpha',0.2,'edgecolor',[1 1 1],'parent',zimg.Parent,'FaceLighting','none','userdata',ncell);
                hold(zimg.Parent,'off');
                
                % rescale...
                oldcmap{ncell} = bgimg.CData(:,:,1);
                r = single(bgimg.CData(:,:,1));
                r(mask>0) = 0;
                r = (r-min(r(:)))/(max(r(:))-min(r(:)));
                bgimg.CData(:,:,1) = uint8(r*255);
                status.String = sprintf('Segmented %d cells',ncell);
                drawnow;
                
                
        end
        
    end
end
