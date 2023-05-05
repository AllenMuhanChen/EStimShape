function [m,T] = sbxalignx_ref(fname,ref,idx)

% Aligns images in fname for all indices in idx to ref
% 
% m - mean image after the alignment
% T - optimal translation for each frame

parfor i=1:N    
    z = squeeze(sbxread(fname,idx,N));
    
        [u v] = fftalign(A,B);

end


