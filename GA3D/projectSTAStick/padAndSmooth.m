function smoothRwa = padAndSmooth(rwa,commonKernel,padding)
    padSize = (size(commonKernel) - 1)/2;
    for ii=1:length(padding)
        pad = zeros(1,length(padding));
        pad(ii) = padSize(ii);
        if padding(ii) == 'c'
            rwa = padarray(rwa,pad,'circular');
        elseif padding(ii) == 'r'
            rwa = padarray(rwa,pad,'replicate');
        else
            rwa = padarray(rwa,pad);
        end
    end
    
    smoothRwa = convn(rwa,commonKernel,'valid');
end

