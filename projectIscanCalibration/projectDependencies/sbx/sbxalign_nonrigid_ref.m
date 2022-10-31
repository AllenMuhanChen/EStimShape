function zr = sbxalign_nonrigid_ref(fname,idx,N,ref)

gref = gpuArray(ref);
z = squeeze(sbxread(fname,idx,N));
gz = gpuArray(z);
parfor(i=1:N)    
    [~,zr{i}] = imregdemons(gz(:,:,i),gref,[32 16 8],'AccumulatedFieldSmoothing',2.5,'PyramidLevels',3,'DisplayWaitBar',false);
end
