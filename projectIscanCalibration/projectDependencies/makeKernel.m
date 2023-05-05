function gaussKernel = makeKernel(binWidths,sigmas,numSigmasToConsider)
    numDims = length(binWidths);
    
    kernelWidthInBins = round((numSigmasToConsider.*sigmas)./binWidths);

    inp = cell(1,numDims);
    for i = 1:numDims
        inp{i} = binWidths(i).*(-kernelWidthInBins(i):1:kernelWidthInBins(i));
    end

    outGrid = cell(1,numDims);
    [outGrid{:}] = ndgrid(inp{:});

    gaussKernel = ones(size(outGrid{1}));
    for i = 1:numDims
       gaussKernel =  gaussKernel.*exp(-1.*(outGrid{i}.*outGrid{i})./(2*sigmas(i)*sigmas(i)));
    end

    gaussKernel = gaussKernel./sum(gaussKernel(:));
end
