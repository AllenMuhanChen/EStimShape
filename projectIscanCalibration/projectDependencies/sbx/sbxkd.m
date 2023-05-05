function sbxkd(src,callbackdata)

global zs ps segmenttool_h

switch callbackdata.Key
    case 'z'
        pan(segmenttool_h,'off');
        ps = 0;
        if(zs>0)
            zs = 0;
            zoom(segmenttool_h,'off');
        else
            zs = 1;
            zoom(segmenttool_h,'on');
        end
    case 'p'
        zoom(segmenttool_h,'off');
        zs = 0;
        if(ps>0)
            ps = 0;
            pan(segmenttool_h,'off');
        else
            ps  = 1;
            pan(segmenttool_h,'on');
        end
end

