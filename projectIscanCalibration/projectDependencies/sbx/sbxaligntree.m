function t = sbxaligntree(idx)

switch length(idx)
    case 1
        t = {idx(1)};
    case 2
        t = {idx(1) idx(2)};
    otherwise
        idx0 = idx(1:floor(end/2));      
        idx1 = idx(floor(end/2)+1 : end);
        t = { sbxaligntree(idx0) sbxaligntree(idx1) };
end

