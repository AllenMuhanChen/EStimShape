function z = sbxreadzstack(fname,chan)

z = sbxread(fname,0,1);
global info
z = sbxread(fname,0,1+info.max_idx);
z = squeeze(z(chan,:,:,:));
nf =  info.config.knobby.schedule(1,end);
z = reshape(z,[size(z,1) size(z,2) nf (info.max_idx+1)/nf]);
z = squeeze(mean(z,3));
z = z/max(z(:));
% normalize intensity across depth

% for i = 1:size(z,3);
%     z(:,:,i) = imadjust(squeeze(z(:,:,i)));
% end


